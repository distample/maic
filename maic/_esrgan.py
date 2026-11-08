"""The ESRGAN generator, rebuilt from a published checkpoint.

An ESRGAN ``.pth`` is a bare state dict: tensors and their names, with nothing
saying how many blocks the network had or how wide they were.  Everything here
exists to read that back out of the tensor shapes, so maic can load a model it
has never seen before without a description alongside it.

The layout reproduced is the original ESRGAN one -- ``model.0``, ``model.1.sub``
and a numbered tail -- because that is what the published models are released
in, down to the dense convolutions being wrapped in a ``Sequential`` with their
activation (hence the ``conv1.0.weight`` in the key names).

Two tails occur in the wild, and which one a file has is read off its keys:

* ending at ``model.4``: no upsampling at all, a true 1x network.  This is what
  the 1x-MangaJPEG models maic uses are;
* ending at ``model.10``: ESRGAN's two upsampling stages kept, fed an image
  pixel-unshuffled by four so the two cancel out.  Older 1x JPEG models were
  trained this way.

Nothing in here is maic-specific; it is deliberately a plain torch module so it
can be tested with a network eight channels wide instead of a 19 MB download.
"""

import torch
from torch import nn
from torch.nn import functional as F

# ESRGAN's own constants: every residual is scaled before it is added back.
RESIDUAL_SCALING = 0.2
NEGATIVE_SLOPE = 0.2


def _conv(in_channels, out_channels, activated=True):
    """A convolution in the ``Sequential`` wrapper the checkpoints were saved with."""
    layers = [nn.Conv2d(in_channels, out_channels, 3, 1, 1)]
    if activated:
        layers.append(nn.LeakyReLU(negative_slope=NEGATIVE_SLOPE, inplace=True))
    return nn.Sequential(*layers)


class ResidualDenseBlock(nn.Module):
    """Five convolutions, each seeing everything before it."""

    def __init__(self, features, growth):
        super().__init__()
        self.conv1 = _conv(features, growth)
        self.conv2 = _conv(features + growth, growth)
        self.conv3 = _conv(features + 2 * growth, growth)
        self.conv4 = _conv(features + 3 * growth, growth)
        self.conv5 = _conv(features + 4 * growth, features, activated=False)

    def forward(self, x):
        x1 = self.conv1(x)
        x2 = self.conv2(torch.cat((x, x1), 1))
        x3 = self.conv3(torch.cat((x, x1, x2), 1))
        x4 = self.conv4(torch.cat((x, x1, x2, x3), 1))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * RESIDUAL_SCALING + x


class RRDB(nn.Module):
    """Three dense blocks in a row, residual around the lot."""

    def __init__(self, features, growth):
        super().__init__()
        self.RDB1 = ResidualDenseBlock(features, growth)
        self.RDB2 = ResidualDenseBlock(features, growth)
        self.RDB3 = ResidualDenseBlock(features, growth)

    def forward(self, x):
        out = self.RDB3(self.RDB2(self.RDB1(x)))
        return out * RESIDUAL_SCALING + x


class _ShortcutBlock(nn.Module):
    """The trunk, with the skip connection ESRGAN puts around it.

    Named ``sub`` because that is the name the published checkpoints carry.
    """

    def __init__(self, sub):
        super().__init__()
        self.sub = sub

    def forward(self, x):
        return x + self.sub(x)


class Generator(nn.Module):
    """An ESRGAN generator that returns a page the size it was given."""

    def __init__(self, channels=1, features=32, blocks=12, growth=32,
                 upsamples=0, shuffle_factor=1):
        super().__init__()
        self.channels = channels
        self.shuffle_factor = max(1, int(shuffle_factor))
        # What the network does to the page overall: the upsampling stages
        # multiply, the unshuffle at the input divides.  A 1x restoration model
        # cancels out; a manga upscaler comes out at 2x or 4x.
        self.scale = (2 ** int(upsamples)) // self.shuffle_factor
        trunk = nn.Sequential(
            *[RRDB(features, growth) for _ in range(blocks)],
            nn.Conv2d(features, features, 3, 1, 1),
        )
        layers = [
            nn.Conv2d(channels * self.shuffle_factor ** 2, features, 3, 1, 1),
            _ShortcutBlock(trunk),
        ]
        for _ in range(upsamples):
            layers += [
                nn.Upsample(scale_factor=2, mode="nearest"),
                nn.Conv2d(features, features, 3, 1, 1),
                nn.LeakyReLU(negative_slope=NEGATIVE_SLOPE, inplace=True),
            ]
        layers += [
            nn.Conv2d(features, features, 3, 1, 1),
            nn.LeakyReLU(negative_slope=NEGATIVE_SLOPE, inplace=True),
            nn.Conv2d(features, channels, 3, 1, 1),
        ]
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        factor = self.shuffle_factor
        if factor <= 1:
            return self.model(x)

        # The unshuffle needs whole blocks, and the last tile of a page is any
        # size at all, so the edges are mirrored out and cut off again after.
        height, width = x.shape[-2:]
        pad_bottom = (factor - height % factor) % factor
        pad_right = (factor - width % factor) % factor
        if pad_bottom or pad_right:
            x = F.pad(x, (0, pad_right, 0, pad_bottom), mode="reflect")
        out = self.model(F.pixel_unshuffle(x, factor))
        # Cut the padding back off -- at the scale the network works at, or a
        # 2x model would come back with only the corner of what it produced.
        return out[..., :height * self.scale, :width * self.scale]


def new_generator(channels=1, features=32, blocks=12, growth=32,
                  upsamples=0, shuffle_factor=1):
    """A generator of the given shape, with freshly initialised weights."""
    return Generator(channels, features, blocks, growth, upsamples, shuffle_factor)


def describe_state_dict(state):
    """The shape of the network *state* came from.

    Raises ``ValueError`` when the keys are not an ESRGAN checkpoint at all --
    which is how a weights file that is something else entirely becomes a line
    in the log rather than a stack trace mid-volume.
    """
    first = state.get("model.0.weight")
    if first is None:
        raise ValueError("not an ESRGAN checkpoint (no model.0 weights)")

    # The tail is a run of numbered convolutions; the last of them writes the
    # image back out, and how many lie between it and the trunk says how many
    # upsampling stages the network had.
    tail = sorted(
        index
        for index in (
            int(key.split(".")[1])
            for key in state
            if key.startswith("model.") and key.endswith(".weight") and key.count(".") == 2
        )
        if index > 1
    )
    if not tail:
        raise ValueError("not an ESRGAN checkpoint (no output convolution)")
    last = state["model.%d.weight" % tail[-1]]

    blocks = 0
    while "model.1.sub.%d.RDB1.conv1.0.weight" % blocks in state:
        blocks += 1
    if not blocks:
        raise ValueError("not an ESRGAN checkpoint (no RRDB blocks)")

    features = int(first.shape[0])
    inputs = int(first.shape[1])
    channels = int(last.shape[0])
    growth = int(state["model.1.sub.0.RDB1.conv1.0.weight"].shape[0])

    # Every upsampling stage is one more convolution in the tail, on top of the
    # two that always close the network.
    upsamples = max(0, len(tail) - 2)

    # A network whose input is wider than the image it emits was fed a
    # pixel-unshuffled page: the unshuffle is what cancels the upsampling.
    shuffle_factor = 1
    if channels and inputs != channels:
        squared, remainder = divmod(inputs, channels)
        shuffle_factor = int(round(squared ** 0.5))
        if remainder or shuffle_factor * shuffle_factor != squared:
            raise ValueError(
                "unsupported ESRGAN input width: %d channels in, %d out" % (inputs, channels)
            )

    return {
        "channels": channels,
        "features": features,
        "blocks": blocks,
        "growth": growth,
        "upsamples": upsamples,
        "shuffle_factor": shuffle_factor,
        # What the network does to the page overall: 1 for every model maic uses.
        "scale": (2 ** upsamples) // shuffle_factor,
    }


def build_generator(state):
    """A generator holding the weights in *state*, shaped to match them."""
    shape = describe_state_dict(state)
    model = Generator(
        channels=shape["channels"],
        features=shape["features"],
        blocks=shape["blocks"],
        growth=shape["growth"],
        upsamples=shape["upsamples"],
        shuffle_factor=shape["shuffle_factor"],
    )
    model.load_state_dict(state)
    return model
