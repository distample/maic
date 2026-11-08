const API = '';
let _lang = {};
let _langCode = localStorage.getItem('mcs_lang') || 'en';
let _availLangs = ['en'];
let _volPrefixes = ['Vol.'];

async function _loadLangs() {
  try {
    const response = await fetch(API + '/api/langs');
    if (response.ok) {
      const data = await response.json();
      _availLangs = data.langs || ['en'];
      _volPrefixes = data.vol_prefixes || ['Vol.'];
    }
  } catch (error) {
    console.warn('Langs list failed:', error);
  }
}

async function _loadLang(code) {
  try {
    const response = await fetch(API + '/api/lang/' + code);
    if (response.ok) {
      _lang = await response.json();
      _langCode = code;
      localStorage.setItem('mcs_lang', code);
    }
  } catch (error) {
    console.warn('Lang load failed:', error);
  }
}

function t(key, fallback) {
  return _lang[key] || fallback || key;
}

function _lsb(key, def) {
  const value = localStorage.getItem('mcs_' + key);
  return value === null ? def : value === 'true';
}

function _lsi(key, def) {
  const value = localStorage.getItem('mcs_' + key);
  return value === null ? def : parseInt(value, 10) || 0;
}

function _lsf(key, def) {
  const value = localStorage.getItem('mcs_' + key);
  return value === null ? def : parseFloat(value) || 0;
}

// Missing-module notices are dismissed independently for this browser origin.
const _dismissedModuleNotices = (() => {
  try {
    const saved = JSON.parse(localStorage.getItem('mcs_dismissedModuleNotices') || '[]');
    return new Set(Array.isArray(saved) ? saved.filter(id => typeof id === 'string') : []);
  } catch (error) {
    return new Set();
  }
})();

function _persistDismissedModuleNotices() {
  try {
    localStorage.setItem('mcs_dismissedModuleNotices', JSON.stringify([..._dismissedModuleNotices]));
  } catch (error) {
    // Dismissal still works for this page when browser storage is unavailable.
  }
}

const _convPersistKeys = [
  'convManga',
  'convGrayscale',
  'convCropping',
  'convMaicCrop',
  'convMaicMarginPct',
  'convMaicWatermarks',
  'convMaicPageNumbers',
  'convMangaUpscale',
  'convScanCleanup',
  'convFacingPages',
  'convForceSpreadPreview',
  'convSpreadPreviewMode',
  'convCroppingPower',
  'convPreserveMarginH',
  'convPreserveMarginV',
  'convSplitter',
  'convUpscale',
  'convStretch',
  'convHQ',
  'convWebtoon',
  'convNoRotate',
  'convKindleDocType',
  'convRotateFirst',
  'convGamma',
  'convGammaAuto',
  'convAutocontrast',
  'convNoAutocontrast',
  'convColorAutocontrast',
  'convAutolevel',
  'convForceColor',
  'convForcePNG',
  'convInterPanelCrop',
  'convEraseRainbow',
  'convPdfLegacy',
  'convSpreadShift',
  'convMatchSpreadWidth',
  'convScreenMargins',
  'convDeleteInput',
  'convNoProcessing',
  'convBatchSplit',
  'convFileFusion',
  'convMetadataTitle',
  'convVolPrefix',
  'convCustomW',
  'convCustomH',
  'convJpegQ',
  'convCustomJpeg',
];
