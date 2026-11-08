// Load languages list, then current language, then render
_loadLangs().then(()=>_loadLang(_langCode)).then(()=>{if(typeof render==='function')render();});
const _KCC_ICON='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAALIklEQVR4nJWXe3Bc1X3HP+c+9u5Dq9WutLt62bJkWZYl/MQ22Ma27NrthClOC5Ey4ZVOSksyqf9IO5OhbVKFdFrKZJiknSaTCQ00Q+MhwsQ0gdo4GJnHmBCMkYWxbJCQJUsraXellfZ99z5O/7DVgY5Dwu+v371n7vl+znd+557fgU8Zg4OD2nIupVQ+OialbC5J+WVbyi/PDL0YABgYGFA/rcYNQ0op+vv7let5bGjk1L8PnnjhwuSl889Xypm/yWcXns5lUvPlqUuyPDcuS1Z5OJVKbFuGllKKG817w5c3EFeFEM61/Or9Lx4/+0jmHW9jW9NqbjrUgD/sBxQWL53DyqbdSlVUOuVFVdS35xTp7Glubh26Po8ihHA/FYAcHNTEvn22lIWm2ctX/3VoeOIuR6js2rDDVuunlVzmsnQcW+aytrDNgOJv2SVyE+cpHD1s51ft1fQNd132mJVD0ebm/Lp16xJSSiGEkL8TYGBgQO3t7ZVCCHcpdeFQas76Yf5qdYM/pjh17X4lX3LF1Ae/wXCfxxGTzE7PYc2so67ldvyVaaKxWoymm2RN+3bhVZUyYBWL5YcCAd8PPuroxwD6+/uVnp4e5fTp0+7DDz/sAlhm6mFLev5h8soMmrpkG8GVmmMJCoU5Ri8fwTZ12loU6lbsJRzuJuCN4wJ5B9JXp5keGZYffjAq9n32s0Si0cXxsdG2DRs2ZJaduLEDQmC67pZUZuEbytLUn75/5gU3lzjOolpQOnsexWO0gjVLw4oQochNCKAwX+T9t9/k0plXCV76NfLDi7w1luTCQpkcyNt7/8T5+sAxLZFI/EVTU9N/SCk1IYQtlm342cCAZ8+ODZ2ax7N3dnK8V04N706cP015/IxT6y+p1opdsPEO1mw+QLRhLTowP5kgeeoYqVO/xH73N6TnMpyag9troCMEpi54MakzUXDpavY6n391WNHr6l+OBPwHlgvy/7bHqVO/CCeTqa/WxOr/cmlmgsyz35E1u+91A7f9uRqqjdO6fjsBFZayBUb++xleeuKnzP7qJHcGSsQMUL3QFVNYGfaRd1UCWh7ddfmDuM2z0wbhXF4ZP/6c6HrgazuunD3bIISY6e/vV8RHt4eUUjt/9pWzRcvtLosq0dLWqbbEgqjA2MhF5o8+iX38Z/gSV6l4VC6aQWoVmx2hEpbjIqREE2B7DDBNLAkq8E4liGHmcXf2OAefflnNJpO94Xj8qJRS066LSyllYPrquyeGXnttY6hjm3ugp1vxej0Mv3GGwe9/n9FfvsCWyhJ3toNbq6Eh6YqUSAo/omISEC6IayVluCa2LlCloOJIuqpMyobC+Mg5WS4U8Ecie4CjAMsrV6ZmLj/37N9967YTJ15xXh9+T6kg+J+fHuGxAwdIHDtGXNcZ9cZ5KRtE1wToGq7r0iBzGLpAeDQUQ0c1PAivgdA0PLEQRkMYKcHj8+LLLonUhXN4NG3b9XJ3tJGR14PzycmnR869fuDVN39uV+fC2mxjKxPpRVqrVB7s9FAbjyNtG8uFuVKIlJ5nhchiu9dWrCBxPR6cUgWBi6qrSNMFv5dwo0427yBVHUMrKOm3z9Byy+61g08+WSOEWFQKBctIJKatuoZ11j3ffYr4bZux5maZmJxk5c4eIiE/VblZ4naGNWKBnmCaqGZioiA1BWloOKqG1hjGt60NJxymLFUcXcc1vGghlVCzge3zEYwFRWroTZkuW+Gm7dtbAZStW/elhapP6bquC9unbb7nK27dhi7GRkbw1Dex0LETy3WRfj9lxaBcVY3e3gjNjVTCtZR1P6bQyc7m8ARsarbF8XQ0URQeCBige4g0GgRiPmyPpDD1gSucCloo1A6gSCmVbG7h2wuZzAOFfHY8mUgoAa9XJlIpHNvG2XGIl5JeKqqBYmi4lo3qd6jeVE3NzTGqb12Jf1sbbn2cQlFD0Syq272ENq9AjYRAA0cp4/fPYKpFgtqsdLNphOptB9Cun05J4MePPfbYkVCV9iO/xr2zpumMvP+huuOP/xB+3kzJYxMAFAGFKyVUn4JWa6BooAdVAg3VuLYEOw+VPDURE8csY86nKZZsLBuijR7E0gKldAI33rkKQPvIweMCsZef/WFX+tKE9IXbxTsX3iPWeJBQU4zcr1/BjfjQXQfHksxl5mm91cDrF8i8jbQr4Fo4uODauJbEkWABIuTBXrKQ0kbarqgsTENsXRPA8p/QfeLfnqibyL1/SvGI1Vpdu+txSszNzzuZbF5V99xF6uRJRK1KTZOO34BsWpIYy7JqrYljgdQFjtCw8xYS0Ko1rAqUsg7BLT6c4QrltIIjEHZmGuHKKIDS19enCCHkbHqqY/SDkdUnhx93XkqckUVDUxSBemVsVPpvOYi2upFCusTiVB6zXGDFJpPmzRoVRcXxCCpCR+2O4NnZgFVXw2JZRWnRMQN+jHobpQ6K6Ci1AnMhgZRuzWD/Xk0ZGBhwAarbI5c6V3Vn1jQ1ia3tVerm1pVvGZo4lkylhOmtdn0HvkC5JMnm4Mo7Nm89bzJ+sUhFuJSRFM0KqfNzaOFFag+q1GwLocc9xHcbSGlh1GkE10dxDCmKyUlc1wmU2nv8ihBCDgz0qoe/eHi+uaHp9IH19yjb47t//KXeL+1ZCDU+uFQoFNMz0yKwv1e60Wr8awPEeiI03BpGj0couBpFVMqGwWJeZ2zQoZK1MGIVlJCGNCwKZQM34MWonsJRq/C13uxYZskbbtjtUwB6e7skgL/G+73aQOuDfXcffkD09VmP9N2eMm33yHw6JURjm6PvPERqNIsTyKGEF5HeBfKWS0ENIFY1UnewDWPdChYW/WQWXBYXbRZzAZaKBvlKDU7rN6j/ykkZ2v+AWspnVVlfb92wIenv71e6u7tFX1+f809PPdUVcJWhrZs2ab6lGTH64B+B7hDfCL4qQIJjg+2At0EQ6W5BGBHwrsRxHMyFdzGLJaS/C+XWn7gLmTkhXOsF3R98ZO+W9W9ov014+fnv77vv4te+/S+vNcVj+9d0dDh19/2VmjnxHE6kDtnkRfXVoVc3ogSbwd9EpWE1SnU9Dn6cskl+6CEqhXPoepT5yYvuiWNHtHik9j/7//m7Z/r7+7WPASz3gctxGhRAjr/79i9CVd790VhMRj7/10Q/dxihaiA0bBckCkWzRD67xOL4LPMT5xifGKN9aw9bWu4ml7iAbjRQLFdY276SPfs+U71u0w41Go3yMYD/H7GLFyUgdXhj4sIQz80m1PY1a3CX5nDMAiW9BoFCMjlBajyNO/kWgUCCarvMnB0g6XhY33k3FacZPC24boauzlWs7VhX2XzzLkcODmqfCPDM0WccgHBb22VPMZ8uZtK1yUlVVkZ+JWLMMloKofj80pJZ/J7tMlDuoLHTlUOVIFbBIuZXlYKtCG+4GyO+0anKpFjb3oHHo1QA6OETHVCQ6ID2o0cfrTz0t1/P+GPRuvXdnZV82FaUwpRS7QmLkuITsWgd0Ya1Qi948QcD3BKQjF56j7mcDUjZuONe/HVNattqk5qgn4mJseCyyCc6AFBVVeXL5/OeilU5XmOEW5obY541e77KYq6IAKTj2IpQclJaS+gsAhljfmkxl14whRHaVRupXRFubOLq2MVv5q3ky8NZszQxkZoEEGK//XvdDbnWucv777+/+94v3Ll7VXNczM+np+dTmfRkamb+wptnl37wk2dyQBFYvnYFvvWPj/zX5774Z59JJZPf3Ld143d+T63fQiB+N6uiKEgphZRSkVKKO+64I/69xx/fANc6bzkwoC6PLX/zv0V0WeHcIJkmAAAAAElFTkSuQmCC';

let S={
  tab:localStorage.getItem('mcs_tab')||'clean',
  // Folder mode
  rootFolder:'',
  cleanSources:JSON.parse(sessionStorage.getItem('mcs_cleanSources')||'[]'),
  outputDir:'',       // export destination
  hasSubfolders:false,
  groups:[], // [{folder, folderName, files:[{name,path,relPath}], isRoot}]
  allFiles:[], // flat list with folder info
  idx:parseInt(sessionStorage.getItem('mcs_idx'))||0,
  cleanViewOpen:sessionStorage.getItem('mcs_cleanViewOpen')!=='false',
  cleanCollapsed:{},  // tree collapse state
  // Tools
  tool:'brush', brushSize:20, showMask:true,
  cleanMethod: localStorage.getItem('mcs_cleanMethod')||'lama', confidence:parseFloat(localStorage.getItem('mcs_confidence'))||0.3,
  maskPadding: parseInt(localStorage.getItem('mcs_maskPadding'))||2,
  processing:false, status:'', showSettings:false,
  // Detections: path -> [boxes]
  detections:{},
  cleanedPaths:{}, // path -> true
  // Batch
  batch:{running:false, phase:'', current:0, total:0, currentFile:'', log:[], detections:{}},
  batchPollId:null,
  progressOwner:'',
  autonomous:{running:false,phase:'idle',current:0,total:0,currentFile:'',progress:0,log:[],processed:0,failed:0,fallbacks:0},
  autonomousPollId:null,
  artifactProfiles:[],artifactCapture:null,artifactDraft:null,artifactSaving:false,showArtifactProfiles:false,
  // Backend
  backend:{status:'checking',device:'cpu',gpu:'',cpu:'CPU',cudaAvailable:false,modelLoaded:false},
  // Train
  trainOrigDir:'',trainCleanDir:'',trainEpochs:30,trainImgSize:640,trainBaseModel:'yolov8n-seg.pt',
  finetuneEpochs:10,finetuneImgSize:640,finetuneDir:'',finetuneModel:'',
  trainStatus:{training:false,progress:0,epoch_current:0,epochs_total:30,log:[]},
  trainPollId:null,
  convSources:JSON.parse(sessionStorage.getItem('mcs_convSources')||'[]'),
  convScanned:{},
  convExpandedSource:sessionStorage.getItem('mcs_convExpandedSource')||null,
  convExclusions:JSON.parse(sessionStorage.getItem('mcs_convExclusions')||'{}'),
  convExcluded:JSON.parse(sessionStorage.getItem('mcs_convExcluded')||'{}'),
  convCustomCrop:JSON.parse(sessionStorage.getItem('mcs_convCustomCrop')||'{}'),
  convCustomSplit:JSON.parse(sessionStorage.getItem('mcs_convCustomSplit')||'{}'),
  convExtraMargin:JSON.parse(sessionStorage.getItem('mcs_convExtraMargin')||'{}'),
  convEditOps:JSON.parse(sessionStorage.getItem('mcs_convEditOps')||'{}'),
  convWatermarkMatches:JSON.parse(sessionStorage.getItem('mcs_convWatermarkMatches')||'{}'),
  convWatermarkReviewed:JSON.parse(sessionStorage.getItem('mcs_convWatermarkReviewed')||'{}'),
  convBookmarks:(JSON.parse(sessionStorage.getItem('mcs_convSources')||'[]').length>0)?JSON.parse(localStorage.getItem('mcs_convBookmarks')||'{}'):{},
  convAutoBmSuppressed:(JSON.parse(sessionStorage.getItem('mcs_convSources')||'[]').length>0)?JSON.parse(localStorage.getItem('mcs_convAutoBmSuppressed')||'{}'):{},
  convBookmarkOrigin:(JSON.parse(sessionStorage.getItem('mcs_convSources')||'[]').length>0)?JSON.parse(localStorage.getItem('mcs_convBookmarkOrigin')||'{}'):{},
  _convBookmarkEdit:false,
  _convExtraMarginEdit:false,
  _convExtraMarginColor:localStorage.getItem('mcs_convExtraMarginColor')||'#ffffff',
  _convEditMode:false,
  _convEditTool:'brush',
  _convEditColor:'#fff',
  _convEditBrushSize:20,
  convViewIdx:sessionStorage.getItem('mcs_convViewIdx')!==null?parseInt(sessionStorage.getItem('mcs_convViewIdx')):null,
  convViewScale:1, convViewX:0, convViewY:0,
  _convSplitStepByRel:{},
  _convSplitOrderByRel:{},
  convCollapsed:{},
  convProfile:localStorage.getItem('mcs_convProfile')||'Kindle_Paperwhite_12',
  convFormat:(()=>{
    const fmt=localStorage.getItem('mcs_convFormat')||'EPUB';
    return String(fmt).toUpperCase()==='KPF'?'KFX':fmt;
  })(),
  convTitle:'',
  convAuthor:'',
  convManga:_lsb('convManga',false),
  convGrayscale:_lsb('convGrayscale',false),
  convCropping:_lsi('convCropping',0),
  convMaicCrop:_lsb('convMaicCrop',false),
  convMaicMarginPct:_lsf('convMaicMarginPct',0.6),
  convMaicWatermarks:_lsb('convMaicWatermarks',false),
  convMaicPageNumbers:_lsb('convMaicPageNumbers',false),
  convMangaUpscale:_lsi('convMangaUpscale',0),
  convScanCleanup:_lsb('convScanCleanup',false),
  convFacingPages:_lsb('convFacingPages',true),
  convForceSpreadPreview:_lsb('convForceSpreadPreview',true),
  convSpreadPreviewMode:(()=>{
    const saved=localStorage.getItem('mcs_convSpreadPreviewMode');
    if(saved!==null)return Math.max(0,Math.min(2,parseInt(saved,10)||0));
    // Migrate the former checkbox: enabled becomes the new selective default.
    return _lsb('convForceSpreadPreview',true)?1:0;
  })(),
  _convFolioMenuOpen:false,
  _convFolioMode:null,
  _convFolioDraft:null,
  _convFolioDigits:'',
  _convFolioSaving:false,
  _convFolioMessage:'',
  _convPageNumberMemoryRevision:'0',
  _convWatermarkMenuOpen:false,
  _convWatermarkCapture:false,
  _convWatermarkDraft:null,
  _convWatermarkSaving:false,
  _convWatermarkMessage:'',
  _convWatermarkRevision:'0',
  convCroppingPower:_lsf('convCroppingPower',1.0),
  convPreserveMarginH:_lsi('convPreserveMarginH',_lsi('convPreserveMargin',0)),
  convPreserveMarginV:_lsi('convPreserveMarginV',_lsi('convPreserveMargin',0)),
  convSplitter:_lsi('convSplitter',0),
  convUpscale:_lsi('convUpscale',0),
  convStretch:_lsb('convStretch',false),
  convHQ:_lsi('convHQ',0),
  convWebtoon:_lsb('convWebtoon',false),
  convNoRotate:_lsb('convNoRotate',false),
  convAutoBalanceMode:(()=>{
    const m=parseInt(localStorage.getItem('mcs_convAutoBalanceMode')||'',10);
    // New UX: 0=Auto, 1=Manual.
    // Backward compatibility with previous tri-state:
    // 2(Auto)->0, 1(PX)->1, 0(Off)->0.
    if([0,1].includes(m))return m;
    if(m===2)return 0;
    const legacyOn=_lsb('convAutoBalanceMargins',false);
    const legacyPx=_lsi('convAutoBalanceMarginPx',0);
    if(!legacyOn)return 0;
    return legacyPx>0?1:0;
  })(),
  convAutoBalanceMarginPx:_lsi('convAutoBalanceMarginPx',24),
  convAutoBalanceMarginUnit:(()=>{
    const u=(localStorage.getItem('mcs_convAutoBalanceMarginUnit')||'px').toLowerCase();
    return ['px','pct'].includes(u)?u:'px';
  })(),
  convAutoBalanceMarginPct:_lsf('convAutoBalanceMarginPct',3.0),
  convKindleDocType:(()=>{
    const v=(localStorage.getItem('mcs_convKindleDocType')||'pdoc').toLowerCase();
    return v==='pdoc'?'pdoc':'ebok';
  })(),
  convRotateFirst:_lsb('convRotateFirst',false),
  convPreviewVariant:'auto',
  convPreviewMode:localStorage.getItem('mcs_convPreviewMode')==='final'?'final':'crop',
  convGamma:_lsf('convGamma',0),
  convGammaAuto:_lsb('convGammaAuto',false),
  convAutocontrast:_lsb('convAutocontrast',false),
  convNoAutocontrast:_lsb('convNoAutocontrast',false),
  convColorAutocontrast:_lsb('convColorAutocontrast',false),
  convAutolevel:_lsb('convAutolevel',false),
  convBordersColor:localStorage.getItem('mcs_convBordersColor')||'none',
  convForceColor:_lsb('convForceColor',false),
  convForcePNG:_lsi('convForcePNG',0),
  convInterPanelCrop:_lsi('convInterPanelCrop',0),
  convEraseRainbow:_lsb('convEraseRainbow',false),
  convPdfLegacy:_lsb('convPdfLegacy',false),
  convChunkSize:_lsi('convChunkSize',0),
  convSpreadShift:_lsb('convSpreadShift',false),
  convMatchSpreadWidth:_lsb('convMatchSpreadWidth',false),
  convScreenMargins:_lsb('convScreenMargins',false),
  convKfxNoPadding:_lsb('convKfxNoPadding',false),
  convDeleteInput:_lsb('convDeleteInput',false),
  convNoProcessing:_lsb('convNoProcessing',false),
  convBatchSplit:_lsi('convBatchSplit',0),
  convFileFusion:_lsb('convFileFusion',false),
  convMetadataTitle:_lsi('convMetadataTitle',0),
  convVolPrefix:localStorage.getItem('mcs_convVolPrefix')||'Vol.',
  convCustomW:_lsi('convCustomW',0),
  convCustomH:_lsi('convCustomH',0),
  convJpegQ:_lsi('convJpegQ',85),
  convCustomJpeg:_lsb('convCustomJpeg',false),
  convAdvancedLog:_lsb('convAdvancedLog',false),
  convPresets:JSON.parse(localStorage.getItem('mcs_convPresets')||'{}'),
  _convShowPresets:false,
  convOutputDir:'',
  convStatus:{converting:false,progress:0,phase:'',current_file:'',total:0,done:0,log:[],output_files:[]},
  convProfiles:null,
  // Whether the Conversion tab is offered at all, and whether it is offered
  // with only the formats that need nothing installed.
  convAvailable:false,
  convNativeOnly:false,
  conv7zAvailable:true,
  convPreviewerAvailable:true,
  convKfxAvailable:false,
  convMobiAvailable:false,
  convMobiTool:null,
  convMobiPath:'',
  convPollId:null,
  convPollInFlight:false,
  _wideThumbByPath:{},
  // Canvas zoom/pan
  viewScale:1, viewX:0, viewY:0,
  // Finetune popup
  showFinetunePopup:false,
  finetuneCorrections:0,
  hideFinetunePopup:localStorage.getItem('mcs_hideFtPopup')==='true',
};

let mainCanvas,mainCtx,maskCanvas,maskCtx;
let painting=false,lastPos=null,rectStart=null,currentImageEl=null;

function browseSourcePaths(result){
  const paths=Array.isArray(result&&result.paths)?result.paths:(result&&result.path?[result.path]:[]);
  return paths.filter(path=>typeof path==='string'&&path.length>0);
}

async function checkBackend(){try{const d=await apiGet('/api/health');S.backend={status:'connected',device:d.device,gpu:d.gpu_name,cpu:d.cpu_name,cudaAvailable:d.cuda_available,modelLoaded:d.model_loaded,kccAvailable:d.kcc_available||false};
  S.kccAvailable=d.kcc_available||false;
  // The three "maic" formats build a volume with nothing installed, so the
  // Conversion tab is offered whenever the backend is up -- trimmed to those
  // formats when KCC is absent rather than hidden altogether.
  S.convAvailable=(d.native_available!==false)||S.kccAvailable;
  if(_volPrefixes.length<=1){await _loadLangs();}
  if(S.convAvailable){try{const cp=await apiGet('/api/convert/profiles');if(!S.convProfiles)S.convProfiles=cp.profiles;S.convMobiAvailable=cp.mobi_available;S.convMobiTool=cp.mobi_tool;S.convMobiPath=cp.mobi_path||'';S.conv7zAvailable=cp.sevenzip_available!==false;S.convPreviewerAvailable=cp.previewer_available!==false;S.convKfxAvailable=cp.kfx_cli_available===true;S.convNativeOnly=cp.native_only===true;}catch(e){}pollConvertStatus();}
  // Also fetch train status for corrections info
  try{const ts=await apiGet('/api/train/status');S.trainStatus=ts;if(ts.training&&!S.trainPollId){S.trainPollId=setInterval(pollTrain,1000);}}catch(e){}
  try{const ap=await apiGet('/api/artifact-profiles');S.artifactProfiles=ap.profiles||[];}catch(e){}
}catch{S.backend.status='disconnected';}render();}
async function setDevice(dev){try{const r=await(await apiPost('/api/set-device',{device:dev})).json();if(r.ok){S.backend.device=r.device;render();}else alert(r.error);}catch(e){alert(e.message);}}

// Encoding-normalized comment.
function showCleanSourceModal(){
  const old=document.getElementById('cleanSrcModal');if(old)old._dismiss?old._dismiss():old.remove();
  const overlay=document.createElement('div');overlay.id='cleanSrcModal';
  Object.assign(overlay.style,{position:'fixed',top:'0',left:'0',width:'100%',height:'100%',
    background:'rgba(0,0,0,0.55)',backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',
    zIndex:'10000',display:'flex',alignItems:'center',justifyContent:'center'});
  const closeModal=()=>overlay._dismiss();
  const modal=document.createElement('div');
  Object.assign(modal.style,{background:'var(--bg2)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
    padding:'1.5rem',minWidth:'16rem',boxShadow:'0 24px 80px rgba(0,0,0,0.5)',display:'flex',flexDirection:'column',gap:'0.7rem'});
  const title=document.createElement('div');title.textContent=t('files.add_source');
  Object.assign(title.style,{fontSize:'0.85rem',fontWeight:'600',color:'var(--text)',textAlign:'center',marginBottom:'0.3rem'});
  modal.append(title);
  const mkBtn=(icon,label,sub,fn)=>{
    const btn=document.createElement('button');btn.type='button';
    Object.assign(btn.style,{display:'flex',alignItems:'center',gap:'0.7rem',padding:'0.7rem 0.9rem',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s',textAlign:'left'});
    btn.onmouseenter=()=>{btn.style.background='var(--glass3)';btn.style.borderColor='var(--accent)';};
    btn.onmouseleave=()=>{btn.style.background='var(--glass2)';btn.style.borderColor='var(--glass-border)';};
    btn.innerHTML=`<span style="font-size:1.4rem">${icon}</span><div><div style="font-size:0.8rem;font-weight:500;color:var(--text)">${label}</div><div style="font-size:0.65rem;color:var(--text3);margin-top:1px">${sub}</div></div>`;
    btn.onclick=()=>{closeModal();fn();};
    return btn;
  };
  modal.append(mkBtn('\ud83d\udcc1',t('source_modal.folder'),t('source_modal.folder_desc'),async()=>{
    try{const r=await(await apiPost('/api/browse-source',{type:'folder',multiple:true})).json();
      const paths=browseSourcePaths(r).filter(path=>!S.cleanSources.includes(path));
      if(paths.length){S.cleanSources.push(...paths);await loadCleanSources();}
    }catch(e){alert(e.message);}
  }));
  modal.append(mkBtn('\ud83d\udce6',t('source_modal.archive'),'CBR, CBZ, ZIP, RAR, 7Z',async()=>{
    try{const r=await(await apiPost('/api/browse-source',{type:'file'})).json();
      if(r.path&&!S.cleanSources.includes(r.path)){S.cleanSources.push(r.path);await loadCleanSources();}
    }catch(e){alert(e.message);}
  }));
  // Cancel action
  const cancel=document.createElement('button');cancel.type='button';
  cancel.textContent=t('source_modal.cancel','Cancel');
  Object.assign(cancel.style,{textAlign:'center',fontSize:'0.72rem',color:'var(--text3)',cursor:'pointer',
    padding:'0.5rem',background:'transparent',transition:'color .2s',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.2rem'});
  cancel.onmouseenter=()=>{cancel.style.color='var(--text2)';};
  cancel.onmouseleave=()=>{cancel.style.color='var(--text3)';};
  cancel.onclick=closeModal;
  modal.append(cancel);
  overlay.append(modal);mountDialog(overlay,modal,t('files.add_source'));
}

async function selectFolder(){
  try{
    const r=await(await apiPost('/api/browse-folder',{})).json();
    if(!r.path)return;
    if(!S.cleanSources.includes(r.path)){S.cleanSources.push(r.path);}
    await loadCleanSources();
  }catch(e){alert(t('clean.error','Error: ')+e.message);}
}

async function loadCleanSources(){
  // Scan all sources and merge into groups/allFiles
  S.groups=[];S.allFiles=[];S.rootFolder=S.cleanSources[0]||'';
  S.status=t('clean.scanning');render();
  const errors=[];
  let hasSubfolders=false;
  for(const [srcIndex,src] of S.cleanSources.entries()){
    try{
      const resp=await apiPost('/api/scan-folder',{path:src});
      if(!resp.ok){errors.push(src+': HTTP '+resp.status);continue;}
      const sr=await resp.json();
      if(sr.ok){
        sr.groups.forEach(g=>{
          S.groups.push(g);
          const sourceBase=src.replace(/[\\/]+$/,'').split(/[\\/]/).pop().replace(/\.[^.]+$/,'')||('source_'+(srcIndex+1));
          const sourceLabel=String(srcIndex+1).padStart(2,'0')+'_'+sourceBase;
          g.files.forEach(f=>{S.allFiles.push({...f,folder:g.folder,folderName:g.folderName,_sourceRoot:src,_sourceLabel:sourceLabel});});
        });
        hasSubfolders=hasSubfolders||!!sr.hasSubfolders;
        if(!S.outputDir&&sr.defaultOutput)S.outputDir=sr.defaultOutput;
      } else {
        errors.push(src+': '+(sr.error||'Unknown error'));
        console.error('[scan-folder]',src,sr.error);
      }
    }catch(e){
      errors.push(src+': '+e.message);
      console.error('[scan-folder] exception',src,e);
    }
  }
  S.hasSubfolders=hasSubfolders||S.groups.length>1;
  S.idx=0;S.detections={};S.cleanedPaths={};
  if(S.allFiles.length>0){
    S.status=`${S.allFiles.length} ${t('clean.files_word','files')} ${t('clean.in_word','in')} ${S.groups.length} ${t('clean.folders_word','folders')}`;
  } else if(errors.length>0){
    S.status='\u26A0 '+errors[0];
  } else {
    S.status=t('clean.no_images','No images found');
  }
  render();setTimeout(loadCurrentImage,50);
}

async function selectOutputFolder(){
  try{
    const r=await(await apiPost('/api/browse-folder',{})).json();
    if(r.path){S.outputDir=r.path;render();}
  }catch(e){alert(e.message);}
}

// Encoding-normalized comment.
function curFile(){return S.allFiles[S.idx]||null;}

async function loadArtifactProfiles(shouldRender=true){
  try{
    const data=await apiGet('/api/artifact-profiles');
    S.artifactProfiles=data.profiles||[];
    if(shouldRender){render();setTimeout(loadCurrentImage,30);}
  }catch(e){S.status=e.message;if(shouldRender)render();}
}
function startArtifactCapture(){
  const f=curFile();if(!f||!S.cleanViewOpen)return;
  if(_maskEditing)cancelMaskEdit();
  S.artifactDraft=null;
  S.artifactCapture={action:'remove',sourcePath:f.path,start:null,current:null};
  S.status=t('artifacts.capture','Select a recurring element, then choose whether to remove or protect it');
  render();setTimeout(loadCurrentImage,30);
}
function cancelArtifactCapture(){
  S.artifactCapture=null;S.artifactDraft=null;S.artifactSaving=false;
  S.status='';render();setTimeout(loadCurrentImage,30);
}
async function saveArtifactDraft(profileId,label,threshold){
  const draft=S.artifactDraft;if(!draft||S.artifactSaving)return;
  S.artifactSaving=true;render();
  try{
    const response=await apiPost('/api/artifact-profiles',{
      source_path:draft.sourcePath,box:draft.box,action:draft.action,
      profile_id:profileId||'',label:String(label||'').trim(),threshold:Number(threshold)||0.88
    });
    const data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||'Failed to save artifact profile');
    S.artifactDraft=null;S.artifactCapture=null;S.artifactSaving=false;
    S.status=t('artifacts.saved','Artifact profile saved');
    await loadArtifactProfiles(false);render();setTimeout(loadCurrentImage,30);
  }catch(e){S.artifactSaving=false;S.status=e.message;alert(e.message);render();setTimeout(loadCurrentImage,30);}
}
async function deleteArtifactProfile(profileId){
  if(!confirm(t('artifacts.delete_confirm','Delete this artifact profile?')))return;
  try{
    const response=await fetch(API+'/api/artifact-profiles/'+encodeURIComponent(profileId),{method:'DELETE'});
    const data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||'Failed to delete profile');
    await loadArtifactProfiles(false);render();setTimeout(loadCurrentImage,30);
  }catch(e){alert(e.message);}
}

// Encoding-normalized comment.
let _maskEditing=false;  // user is currently editing (uncommitted)
let _maskBeforeEdit=null; // mask state before editing started (for cancel)
let _undoStack=[];        // undo history (ImageData arrays)
let _redoStack=[];

function _snapshotMask(){
  if(!maskCtx||!maskCanvas)return null;
  return new Uint8ClampedArray(maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height).data);
}
function _restoreMask(data){
  if(!maskCtx||!maskCanvas||!data)return;
  const id=maskCtx.createImageData(maskCanvas.width,maskCanvas.height);
  id.data.set(data);maskCtx.putImageData(id,0,0);drawOverlay();
}
function _pushUndo(){
  const snap=_snapshotMask();
  if(snap){_undoStack.push(snap);if(_undoStack.length>30)_undoStack.shift();}
  _redoStack=[];
}
function maskUndo(){
  if(_undoStack.length===0)return;
  _redoStack.push(_snapshotMask());
  const data=_undoStack.pop();
  _restoreMask(data);
  if(curFile()) curFile()._maskData=new Uint8ClampedArray(data);
  render();setTimeout(loadCurrentImage,30);
}
function maskRedo(){
  if(_redoStack.length===0)return;
  _undoStack.push(_snapshotMask());
  const data=_redoStack.pop();
  _restoreMask(data);
  if(curFile()) curFile()._maskData=new Uint8ClampedArray(data);
  render();setTimeout(loadCurrentImage,30);
}

function _startEditing(){
  if(!_maskEditing){
    _maskBeforeEdit=_snapshotMask();
    _undoStack=[];_redoStack=[];
    _maskEditing=true;
  }
}
function confirmMaskEdit(){
  if(!_maskEditing)return;
  _maskEditing=false;
  _maskBeforeEdit=null;
  _undoStack=[];_redoStack=[];
  const f=curFile();
  if(maskCanvas&&f){
    const d=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);
    f._maskData=new Uint8ClampedArray(d.data);
    // Check if mask has any red pixels (non-empty)
    let hasContent=false;
    for(let i=0;i<d.data.length;i+=4){
      if(d.data[i]>127&&d.data[i+3]>127){hasContent=true;break;}
    }
    if(hasContent){
      // Mark as having detections (user-defined mask)
      if(!S.detections[f.path]) S.detections[f.path]={boxes:[],masks:[]};
      S.detections[f.path]._userMask=true; // flag: use canvas mask, not auto
      S.status=t('clean.mask_saved');
    } else {
      // Empty mask - remove from processing
      delete S.detections[f.path];
      S.status=t('clean.mask_empty_excluded');
      apiPost('/api/batch/remove-detection',{path:f.path}).catch(()=>{});
    }
    _syncMaskToServer(f.path);
  }
  render();setTimeout(loadCurrentImage,30);
}
function cancelMaskEdit(){
  if(!_maskEditing)return;
  _maskEditing=false;
  if(_maskBeforeEdit){
    _restoreMask(_maskBeforeEdit);
    // Also restore to file state
    if(curFile()) curFile()._maskData=_maskBeforeEdit;
  } else {
    // No prior mask - clear
    if(maskCtx) maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);
    drawOverlay();
  }
  _maskBeforeEdit=null;_undoStack=[];_redoStack=[];
  S.status=t('clean.changes_undone');
  render();setTimeout(loadCurrentImage,30);
}

function saveMask(){
  // Only called on nav/tab switch - saves current state silently (no sync)
  if(!maskCanvas||!curFile())return;
  const d=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);
  curFile()._maskData=new Uint8ClampedArray(d.data);
}

function _syncMaskToServer(path){
  if(!maskCanvas)return;
  (async()=>{
    try{
      const blob=await new Promise(r=>maskCanvas.toBlob(r,'image/png'));
      const fd=new FormData();
      fd.append('path',path);
      fd.append('mask',blob,'mask.png');
      await apiPost('/api/batch/set-mask',fd);
    }catch(e){console.error('mask sync:',e);}
  })();
}

// mtime cache: path -> last known mtime
const _mtimeCache={};

async function _checkFileMtimes(){
  // Check current file and nearby files for external changes
  const visible=[];
  const start=Math.max(0,S.idx-3);
  const end=Math.min(S.allFiles.length,S.idx+4);
  for(let i=start;i<end;i++){if(S.allFiles[i])visible.push(S.allFiles[i].path);}
  if(visible.length===0)return;
  try{
    const r=await(await apiPost('/api/file-mtimes',{paths:visible})).json();
    let changed=false;
    for(const [p,mt] of Object.entries(r)){
      if(_mtimeCache[p]&&_mtimeCache[p]!==mt){
        // File was modified externally
        S.cleanedPaths[p]=Date.now();
        changed=true;
      }
      _mtimeCache[p]=mt;
    }
    if(changed)render();
  }catch(e){}
}

function loadCurrentImage(){
  const f=curFile();if(!f)return;
  if(!S.cleanViewOpen)return;
  _checkFileMtimes();
  mainCanvas=$('mainCanvas');maskCanvas=$('maskCanvas');
  if(!mainCanvas||!maskCanvas){
    requestAnimationFrame(loadCurrentImage);
    return;
  }
  // Hide canvas until new image loads to prevent flash
  mainCanvas.style.visibility='hidden';
  mainCtx=mainCanvas.getContext('2d');maskCtx=maskCanvas.getContext('2d');
  const _thisImg=new Image();
  currentImageEl=_thisImg;
  currentImageEl.onload=()=>{
    // Encoding-normalized comment.
    if(currentImageEl!==_thisImg)return;
    mainCanvas.width=currentImageEl.width;mainCanvas.height=currentImageEl.height;
    maskCanvas.width=currentImageEl.width;maskCanvas.height=currentImageEl.height;
    mainCtx.drawImage(currentImageEl,0,0);
    if(f._maskData){const id=maskCtx.createImageData(currentImageEl.width,currentImageEl.height);id.data.set(f._maskData);maskCtx.putImageData(id,0,0);}
    else{maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);
      const det=S.detections[f.path];
      if(det){
        maskCtx.globalCompositeOperation='source-over';maskCtx.fillStyle='rgba(255,50,50,1)';
        const masks=det.masks||[];
        const boxes=det.boxes||[];
        if(masks.length>0){
          masks.forEach(poly=>{
            if(poly.length<3)return;
            maskCtx.beginPath();
            maskCtx.moveTo(poly[0][0],poly[0][1]);
            for(let i=1;i<poly.length;i++) maskCtx.lineTo(poly[i][0],poly[i][1]);
            maskCtx.closePath();maskCtx.fill();
          });
        } else if(boxes.length>0){
          boxes.forEach(([x1,y1,x2,y2])=>{maskCtx.fillRect(x1-5,y1-5,(x2-x1)+10,(y2-y1)+10);});
        }
      }
    }
    // Encoding-normalized comment.
    const _freshCanvas=$('mainCanvas');
    if(_freshCanvas){mainCanvas=_freshCanvas;mainCtx=mainCanvas.getContext('2d');
      mainCtx.drawImage(_thisImg,0,0);
      if(S.showMask&&maskCanvas){mainCtx.save();mainCtx.globalAlpha=0.45;mainCtx.drawImage(maskCanvas,0,0);mainCtx.restore();}
    }
    mainCanvas.style.visibility='visible';
    mainCanvas.classList.add('loaded');
    _applyView();
    drawOverlay();
  };
  let imgSrc=API+'/api/serve-image?path='+encodeURIComponent(f.path);
  const _imgEpoch=S.cleanedPaths[f.path]||(S._thumbEpoch&&S._thumbEpoch[f.path])||0;
  if(_imgEpoch)imgSrc+='&t='+_imgEpoch;
  currentImageEl.src=imgSrc;
}

let _cursorPos=null; // {x,y} in canvas coords for brush cursor
function drawOverlay(){
  if(!mainCtx||!currentImageEl||!currentImageEl.complete)return;
  mainCtx.drawImage(currentImageEl,0,0);
  if(S.showMask&&maskCanvas){mainCtx.save();mainCtx.globalAlpha=0.45;mainCtx.drawImage(maskCanvas,0,0);mainCtx.restore();}
  const artifactBox=S.artifactDraft&&S.artifactDraft.sourcePath===(curFile()&&curFile().path)?S.artifactDraft.box:null;
  const liveCapture=S.artifactCapture&&S.artifactCapture.start&&S.artifactCapture.current;
  if(artifactBox||liveCapture){
    const action=(S.artifactDraft||S.artifactCapture||{}).action;
    let box=artifactBox;
    if(liveCapture){
      const a=S.artifactCapture.start,b=S.artifactCapture.current;
      box=[Math.min(a.x,b.x),Math.min(a.y,b.y),Math.max(a.x,b.x),Math.max(a.y,b.y)];
    }
    mainCtx.save();mainCtx.strokeStyle=action==='exclude'?'#f59e0b':'#a855f7';mainCtx.lineWidth=3;mainCtx.setLineDash([8,5]);
    mainCtx.strokeRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);mainCtx.setLineDash([]);mainCtx.restore();
  }
  // Draw brush cursor - Photoshop style crisp solid circle
  if(_cursorPos&&(S.tool==='brush'||S.tool==='eraser')){
    mainCtx.save();
    mainCtx.imageSmoothingEnabled=false;
    const cx=Math.round(_cursorPos.x)+0.5;
    const cy=Math.round(_cursorPos.y)+0.5;
    const r=Math.round(S.brushSize/2);
    // Dark outline
    mainCtx.strokeStyle='#000';
    mainCtx.globalAlpha=0.65;
    mainCtx.lineWidth=2;
    mainCtx.beginPath();
    mainCtx.arc(cx,cy,r,0,Math.PI*2);
    mainCtx.stroke();
    // White core
    mainCtx.strokeStyle='#fff';
    mainCtx.globalAlpha=0.95;
    mainCtx.lineWidth=1;
    mainCtx.beginPath();
    mainCtx.arc(cx,cy,r,0,Math.PI*2);
    mainCtx.stroke();
    mainCtx.restore();
  }
}

// Encoding-normalized comment.
let _panning=false, _panStart={x:0,y:0};
function getPos(e){
  const r=mainCanvas.getBoundingClientRect();
  // Account for CSS transform (scale + translate)
  const cssW=r.width/S.viewScale, cssH=r.height/S.viewScale;
  const cx=e.clientX-r.left, cy=e.clientY-r.top;
  return{x:cx/r.width*mainCanvas.width, y:cy/r.height*mainCanvas.height};
}
function paintLine(x1,y1,x2,y2){maskCtx.globalCompositeOperation=S.tool==='eraser'?'destination-out':'source-over';maskCtx.strokeStyle='rgba(255,50,50,1)';maskCtx.lineWidth=S.brushSize;maskCtx.lineCap='round';maskCtx.lineJoin='round';maskCtx.beginPath();maskCtx.moveTo(x1,y1);maskCtx.lineTo(x2,y2);maskCtx.stroke();drawOverlay();}
function paintDot(x,y){maskCtx.globalCompositeOperation=S.tool==='eraser'?'destination-out':'source-over';maskCtx.fillStyle='rgba(255,50,50,1)';maskCtx.beginPath();maskCtx.arc(x,y,S.brushSize/2,0,Math.PI*2);maskCtx.fill();drawOverlay();}
function onMD(e){
  if(!curFile())return;
  if(e.button===1||e.button===2||(e.button===0&&e.altKey)){e.preventDefault();_panning=true;_panStart={x:e.clientX-S.viewX,y:e.clientY-S.viewY};return;}
  if(S.artifactCapture){
    if(e.button!==0)return;e.preventDefault();
    const p=getPos(e);S.artifactCapture.start=p;S.artifactCapture.current=p;drawOverlay();return;
  }
  _startEditing();
  _pushUndo();
  const p=getPos(e);if(S.tool==='rect'){rectStart=p;}else{painting=true;lastPos=p;paintDot(p.x,p.y);}
}
function onMM(e){
  if(_panning){S.viewX=e.clientX-_panStart.x;S.viewY=e.clientY-_panStart.y;_applyView();_updateResetBtn();return;}
  if(!curFile())return;const p=getPos(e);
  if(S.artifactCapture&&S.artifactCapture.start){S.artifactCapture.current=p;drawOverlay();return;}
  _cursorPos=p;
  if(S.tool==='rect'&&rectStart){drawOverlay();mainCtx.strokeStyle='rgba(255,50,50,.8)';mainCtx.lineWidth=2;mainCtx.setLineDash([6,4]);mainCtx.strokeRect(rectStart.x,rectStart.y,p.x-rectStart.x,p.y-rectStart.y);mainCtx.setLineDash([]);}
  else if(painting&&lastPos){paintLine(lastPos.x,lastPos.y,p.x,p.y);lastPos=p;}
  else{drawOverlay();} // just update cursor
}
function onMU(e){
  if(_panning){_panning=false;return;}
  if(!curFile())return;
  if(S.artifactCapture&&S.artifactCapture.start){
    const p=getPos(e),a=S.artifactCapture.start;
    const box=[Math.max(0,Math.round(Math.min(a.x,p.x))),Math.max(0,Math.round(Math.min(a.y,p.y))),
      Math.min(mainCanvas.width,Math.round(Math.max(a.x,p.x))),Math.min(mainCanvas.height,Math.round(Math.max(a.y,p.y)))];
    if(box[2]-box[0]>=4&&box[3]-box[1]>=4){
      const action=S.artifactCapture.action,sourcePath=S.artifactCapture.sourcePath;
      S.artifactDraft={action,sourcePath,box};S.artifactCapture=null;
      render();setTimeout(loadCurrentImage,30);
    }else{S.artifactCapture.start=null;S.artifactCapture.current=null;drawOverlay();}
    return;
  }
  if(S.tool==='rect'&&rectStart){const p=getPos(e);maskCtx.globalCompositeOperation='source-over';maskCtx.fillStyle='rgba(255,50,50,1)';maskCtx.fillRect(Math.min(rectStart.x,p.x),Math.min(rectStart.y,p.y),Math.abs(p.x-rectStart.x),Math.abs(p.y-rectStart.y));rectStart=null;drawOverlay();}
  painting=false;lastPos=null;
  // Save mask data without reloading image
  if(maskCtx&&curFile()){
    const d=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);
    curFile()._maskData=new Uint8ClampedArray(d.data);
  }
}
function onML(e){
  // Mouse leave - hide cursor, stop painting
  _cursorPos=null;
  if(painting){painting=false;lastPos=null;}
  drawOverlay();
}
function _applyView(){
  if(!mainCanvas)return;
  mainCanvas.style.transform=`translate(${S.viewX}px,${S.viewY}px) scale(${S.viewScale})`;
}
function onWheel(e){
  if(!curFile()||!mainCanvas)return;
  e.preventDefault();
  // Alt+wheel: resize brush
  if(e.altKey){
    const step=e.deltaY>0?-2:2;
    S.brushSize=Math.max(2,Math.min(100,S.brushSize+step));
    const bsL=$('bsL');if(bsL)bsL.textContent=S.brushSize;
    const sl=document.querySelector('input[type=range]');if(sl)sl.value=S.brushSize;
    if(_cursorPos)drawOverlay();
    return;
  }
  const delta=e.deltaY>0?0.9:1.1;
  const newScale=Math.max(0.5,Math.min(8,S.viewScale*delta));
  // Zoom toward cursor
  const r=mainCanvas.getBoundingClientRect();
  const cx=e.clientX-r.left-r.width/2;
  const cy=e.clientY-r.top-r.height/2;
  const ratio=newScale/S.viewScale;
  S.viewX-=cx*(ratio-1);
  S.viewY-=cy*(ratio-1);
  S.viewScale=newScale;
  _applyView();
  _updateResetBtn();
}
function _updateResetBtn(){
  const btn=document.getElementById('cleanResetBtn');
  if(btn)btn.style.display=(S.viewScale!==1||S.viewX!==0||S.viewY!==0)?'flex':'none';
}
function resetView(){S.viewScale=1;S.viewX=0;S.viewY=0;if(mainCanvas)mainCanvas.style.transform='';_updateResetBtn();}
function _invalidateCropCaches(clearResults=true){if(clearResults)_convCropRequests.clear();S._cropCache=null;S._cropCachePair=null;S._cropCachePairUnified=null;S._cropCacheSingleUnified=null;S._editCrop=null;}
function convResetView(){S.convViewScale=1;S.convViewX=0;S.convViewY=0;_invalidateCropCaches(false);S._convBookmarkEdit=false;S._convFolioDraft=null;S._convWatermarkDraft=null;}

function _convPageNumberScope(){return S.convExpandedSource||S.convSources[0]||'';}
function _convDetectedPageNumbers(decision){
  if(!decision||decision.has_page_number===false)return [];
  return Object.values(decision.recognizedDigits||{})
    .map(value=>String(value)).filter(value=>/^\d{1,4}$/.test(value));
}
function _convPageNumberChapter(file,scope){
  let chapter='',folder=null;
  for(const current of ((S.convScanned||{})[scope]||[])){
    const currentFolder=current.folder||String(current.relPath||'').replace(/\\/g,'/').split('/').slice(0,-1).join('/');
    if(currentFolder!==folder){folder=currentFolder;chapter=folder;}
    if((S.convBookmarks||{})[current.relPath])chapter=folder+'|'+current.relPath;
    if(current.path===file.path)return chapter;
  }
  return file.folder||'';
}
function _convPageNumberMinimum(file,scope){
  if((S.convExcluded||{})[file.relPath])return 1;
  let minimum=1;
  for(const current of ((S.convScanned||{})[scope]||[])){
    if(current.path===file.path)break;
    if((S.convExcluded||{})[current.relPath])continue;
    // Printed folios continue across folders and bookmarks within a volume.
    const numbers=((S.convPageNumberMatches||{})[current.path]||[])
      .map(Number).filter(number=>Number.isInteger(number)&&number>=minimum);
    if(numbers.length)minimum=Math.max(...numbers)+1;
  }
  return minimum;
}
function _convRecordPageNumbers(path,decision){
  if(!Object.values(S.convScanned||{}).some(files=>files.some(file=>file.path===path)))return;
  if(!S.convPageNumberMatches)S.convPageNumberMatches={};
  const owner=Object.entries(S.convScanned||{}).find(([,files])=>files.some(file=>file.path===path));
  const file=owner[1].find(file=>file.path===path);
  const minimum=_convPageNumberMinimum(file,owner[0]);
  const numbers=_convDetectedPageNumbers(decision).filter(text=>Number(text)>=minimum);
  const changed=JSON.stringify(S.convPageNumberMatches[path]||[])!==JSON.stringify(numbers);
  if(numbers.length)S.convPageNumberMatches[path]=numbers;
  else delete S.convPageNumberMatches[path];
  return changed;
}
function _convUpdatePageNumberBadges(scope){
  const files=new Map((((S.convScanned||{})[scope])||[]).map(file=>[file.path,file]));
  for(const badge of document.querySelectorAll('.conv-page-number-badge')){
    if(badge.getAttribute('data-page-number-scope')!==scope)continue;
    const file=files.get(badge.getAttribute('data-page-number-path'));
    const numbers=file&&S.convMaicPageNumbers&&!(S.convExcluded||{})[file.relPath]
      ?((S.convPageNumberMatches||{})[file.path]||[])
        .filter(text=>Number(text)>=_convPageNumberMinimum(file,scope)):[];
    const text=numbers.length?'\u2460 num '+numbers.join(', '):'';
    if(badge.textContent!==text)badge.textContent=text;
    badge.hidden=!text;
  }
}
function _convRefreshPageNumberResults(scope){
  _convUpdatePageNumberBadges(scope);
  const preview=document.querySelector('.canvas-area');
  if(preview&&preview._refreshPageNumbers)preview._refreshPageNumbers(scope);
}
const _convPageNumberScans=new Map();
async function _convScanPageNumbers(scope){
  const files=(S.convScanned&&S.convScanned[scope])||[];
  const revision=S._convPageNumberMemoryRevision;
  if(!scope||!files.length)return 0;
  const token={};_convPageNumberScans.set(scope,token);
  let matched=0;
  let chapterMinimums={};
  try{
    // A whole-volume scan can monopolize the server while the opened page is
    // still loading. Let image and crop-preview requests run between batches.
    const batchSize=12;
    for(let offset=0;offset<files.length;offset+=batchSize){
      await new Promise(resolve=>setTimeout(resolve,30));
      if(_convPageNumberScans.get(scope)!==token||S.convScanned[scope]!==files||
        S._convPageNumberMemoryRevision!==revision||!S.convMaicPageNumbers)return matched;
      const batch=files.slice(offset,offset+batchSize);
      const response=await apiPost('/api/page-number-examples/rescan',{
        scope_path:scope,chapter_minimums:chapterMinimums,
        files:batch.map(file=>({path:file.path,relPath:file.relPath,chapter_key:_convPageNumberChapter(file,scope)}))
      });
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'Rescan failed');
      if(_convPageNumberScans.get(scope)!==token||S.convScanned[scope]!==files||
        S._convPageNumberMemoryRevision!==revision||!S.convMaicPageNumbers)return matched;
      chapterMinimums=result.chapterMinimums||chapterMinimums;
      batch.forEach(file=>_convRecordPageNumbers(file.path,null));
      (result.matches||[]).forEach(match=>_convRecordPageNumbers(match.path,match));
      matched+=Number(result.matchedCount)||0;
      _convRefreshPageNumberResults(scope);
    }
    return matched;
  }finally{
    if(_convPageNumberScans.get(scope)===token)_convPageNumberScans.delete(scope);
  }
}
async function _convRescanPageNumbers(scope){
  const files=(S.convScanned&&S.convScanned[scope])||[];
  if(!scope||!files.length)return;
  S._convFolioMessage=t('conv.folio_rescanning','Перепроверяю страницы тома…');render();
  try{
    const matchedCount=await _convScanPageNumbers(scope);
    S._convFolioMessage=t('conv.folio_rescan_done','Пример сохранён. Найдено похожих страниц: {count}')
      .replace('{count}',String(matchedCount));
  }catch(error){
    S._convFolioMessage=t('conv.folio_saved_rescan_failed','Пример сохранён, но повторная проверка не завершилась: {error}')
      .replace('{error}',String(error&&error.message||error));
  }
  render();
}
async function _convSavePageNumberExample(file){
  const draft=S._convFolioDraft;
  const scope=_convPageNumberScope();
  if(!file||!draft||S._convFolioSaving)return;
  const digits=String(S._convFolioDigits||'').trim();
  if(draft.action==='number'&&!/^\d{1,4}$/.test(digits)){
    S._convFolioMessage=t('conv.folio_digits_error','Введите от 1 до 4 цифр номера.');render();return;
  }
  S._convFolioSaving=true;S._convFolioMessage=t('conv.folio_saving','Сохраняю пример…');render();
  try{
    const response=await apiPost('/api/page-number-examples',{
      source_path:file.path,scope_path:scope,box:draft.box,action:draft.action,digits
    });
    const result=await response.json();
    if(!response.ok||!result.ok)throw new Error(result.error||'Save failed');
    S._convPageNumberMemoryRevision=String(result.revision||Date.now());
    S._convFolioMode=null;S._convFolioDraft=null;S._convFolioDigits='';
    _invalidateCropCaches();
    S._convFolioSaving=false;
    _convRescanPageNumbers(scope);
    return;
  }catch(error){
    S._convFolioMessage=t('conv.folio_save_failed','Не удалось сохранить пример: {error}')
      .replace('{error}',String(error&&error.message||error));
  }
  S._convFolioSaving=false;render();
}

async function _convRescanWatermarks(scope,profileId){
  const files=(S.convScanned&&S.convScanned[scope])||[];
  if(!scope||!files.length)return;
  S._convWatermarkMessage=t('conv.watermark_rescanning','Checking the source for this watermark…');render();
  try{
    const response=await apiPost('/api/artifact-profiles/rescan',{
      profile_id:profileId||'',
      files:files.map(file=>({path:file.path,relPath:file.relPath}))
    });
    const result=await response.json();
    if(!response.ok||!result.ok)throw new Error(result.error||'Rescan failed');
    const sourceMatches={};
    (Array.isArray(result.matches)?result.matches:[]).forEach(item=>{
      const rel=_convNormPath(item&&item.relPath);
      if(rel)sourceMatches[rel]=Math.max(1,Array.isArray(item.matches)?item.matches.length:1);
    });
    S.convWatermarkMatches=Object.assign({},S.convWatermarkMatches||{}, {[scope]:sourceMatches});
    sessionStorage.setItem('mcs_convWatermarkMatches',JSON.stringify(S.convWatermarkMatches));
    S._convWatermarkMessage=t('conv.watermark_rescan_done','Sample saved. Matching pages found: {count}')
      .replace('{count}',String(result.matchedCount||0));
  }catch(error){
    S._convWatermarkMessage=t('conv.watermark_saved_rescan_failed','Sample saved, but the source check failed: {error}')
      .replace('{error}',String(error&&error.message||error));
  }
  _invalidateCropCaches();render();
}

const _convWatermarkScans=new Map();
let _convWatermarkScanQueue=Promise.resolve();
function _convAutoScanWatermarks(scopes){
  if(!S.convMaicWatermarks)return Promise.resolve(true);
  const requests=[...new Set(scopes||[])].filter(scope=>S.convSources.includes(scope)&&
    Array.isArray(S.convScanned[scope])&&S.convScanned[scope].length).map(scope=>{
    if(S.convWatermarkReviewed[scope])return Promise.resolve(true);
    if(_convWatermarkScans.has(scope))return _convWatermarkScans.get(scope);
    const pending=_convWatermarkScanQueue.then(()=>{
      const isCurrent=()=>_convWatermarkScans.get(scope)===pending&&S.convSources.includes(scope);
      if(!isCurrent())return false;
      return _convRunWatermarkScan([scope],isCurrent);
    });
    _convWatermarkScans.set(scope,pending);
    _convWatermarkScanQueue=pending.catch(()=>false);
    pending.then(()=>{
      if(_convWatermarkScans.get(scope)===pending)_convWatermarkScans.delete(scope);
    },()=>{
      if(_convWatermarkScans.get(scope)===pending)_convWatermarkScans.delete(scope);
    });
    return pending;
  });
  return Promise.all(requests).then(results=>results.every(Boolean));
}
async function _convRunWatermarkScan(scopes,isCurrent){
  const sources=[...new Set((Array.isArray(scopes)?scopes:[]).filter(scope=>
    scope&&!S.convWatermarkReviewed[scope]&&Array.isArray(S.convScanned&&S.convScanned[scope])&&S.convScanned[scope].length))];
  if(!S.convMaicWatermarks||!sources.length)return true;
  const token=String(Date.now())+Math.random();
  S._convWatermarkAutoScanToken=token;
  S._convWatermarkMessage=t('conv.watermark_rescanning','Checking the source for this watermark…');render();
  let matchedTotal=0;
  try{
    for(const scope of sources){
      const files=(S.convScanned&&S.convScanned[scope])||[];
      const response=await apiPost('/api/artifact-profiles/rescan',{
        profile_id:'',files:files.map(file=>({path:file.path,relPath:file.relPath}))
      });
      const result=await response.json();
      if(!isCurrent())return false;
      if(!response.ok||!result.ok)throw new Error(result.error||'Rescan failed');
      const sourceMatches={};
      (Array.isArray(result.matches)?result.matches:[]).forEach(item=>{
        const rel=_convNormPath(item&&item.relPath);
        if(rel)sourceMatches[rel]=Math.max(1,Array.isArray(item.matches)?item.matches.length:1);
      });
      S.convWatermarkMatches={...(S.convWatermarkMatches||{}),[scope]:sourceMatches};
      S.convWatermarkReviewed={...(S.convWatermarkReviewed||{}),[scope]:true};
      matchedTotal+=Object.keys(sourceMatches).length;
    }
    sessionStorage.setItem('mcs_convWatermarkMatches',JSON.stringify(S.convWatermarkMatches));
    sessionStorage.setItem('mcs_convWatermarkReviewed',JSON.stringify(S.convWatermarkReviewed));
    if(S._convWatermarkAutoScanToken===token){
      S._convWatermarkMessage=t('conv.watermark_auto_scan_done','Watermark check complete. Matching pages: {count}')
        .replace('{count}',String(matchedTotal));
    }
  }catch(error){
    if(S._convWatermarkAutoScanToken===token){
      S._convWatermarkMessage=t('conv.watermark_auto_scan_failed','Could not check watermarks: {error}')
        .replace('{error}',String(error&&error.message||error));
    }
    _invalidateCropCaches();render();
    return false;
  }
  _invalidateCropCaches();render();
  return true;
}

async function _convSaveWatermarkDraft(file,profileId,label){
  const draft=S._convWatermarkDraft;
  const scope=S.convExpandedSource||S.convSources[0]||'';
  if(!file||!draft||S._convWatermarkSaving)return;
  const safeLabel=String(label||'').trim();
  if(!profileId&&!safeLabel){
    S._convWatermarkMessage=t('conv.watermark_name_error','Enter a watermark name.');render();return;
  }
  S._convWatermarkSaving=true;
  S._convWatermarkMessage=t('conv.watermark_saving','Saving watermark sample…');render();
  try{
    const response=await apiPost('/api/artifact-profiles',{
      source_path:file.path,
      box:draft.box,
      action:'remove',
      profile_id:profileId||'',
      label:safeLabel||t('conv.watermark_default_name','Watermark'),
      threshold:0.88
    });
    const result=await response.json();
    if(!response.ok||!result.ok)throw new Error(result.error||'Save failed');
    S._convWatermarkSaving=false;S._convWatermarkCapture=false;S._convWatermarkDraft=null;
    S._convWatermarkRevision=String(Date.now());
    await loadArtifactProfiles(false);
    _invalidateCropCaches();render();
    await _convRescanWatermarks(scope,'');
  }catch(error){
    S._convWatermarkSaving=false;
    S._convWatermarkMessage=t('conv.watermark_save_failed','Could not save the watermark sample: {error}')
      .replace('{error}',String(error&&error.message||error));
    render();
  }
}

// The volume a source folder is: "Berserk-01" is 1, "Berserk v03" is 3. An
// explicit volume word wins; otherwise the last number in the name that is
// not a year or a resolution. Letters are excluded before the word by hand,
// since \b does not know Cyrillic.
function convVolumeNumber(folder){
  const s=(folder||'').replace(/\\/g,'/').split('/').filter(Boolean).pop()||'';
  const explicit=s.match(/(?:^|[^A-Za-zА-Яа-яЁё])(?:том|vol(?:ume)?|v|book|кн(?:ига)?)[.\-_\s#]*(\d{1,3})(?!\d)/i);
  if(explicit)return parseInt(explicit[1],10);
  const nums=[...s.matchAll(/\d+/g)].map(m=>parseInt(m[0],10)).filter(n=>n>0&&n<1000);
  return nums.length>0?nums[nums.length-1]:null;
}

function convChapterNumber(folder){
  const s=(folder||'').replace(/\\/g,'/').split('/').pop()||'';
  const explicitAll=[...s.matchAll(/(?:ch(?:apter)?|ep(?:isode)?|part|том|глава|гл)[.\-_\s#]*(\d+(?:[.,]\d+)?)/gi)];
  if(explicitAll.length>0){
    const last=explicitAll[explicitAll.length-1];
    return parseFloat(last[1].replace(',','.'));
  }
  const bracketed=s.match(/[\[(](\d{1,4}(?:[.,]\d+)?)[\])]/);
  if(bracketed)return parseFloat(bracketed[1].replace(',','.'));
  const nums=[...s.matchAll(/(\d+(?:[.,]\d+)?)/g)].map(m=>m[1]);
  if(nums.length>0){
    const n=parseFloat(nums[nums.length-1].replace(',','.'));
    if(n>0&&n<10000)return n;
  }
  return null;
}

function convGuessChapterName(folder){
  const n=convChapterNumber(folder);
  return n===null?'':t('toc.chapter','Chapter')+' '+n;
}

function convMagnifierIcon(){
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('width','12');svg.setAttribute('height','12');
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');
  svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','2.2');
  svg.setAttribute('stroke-linecap','round');
  const lens=document.createElementNS(ns,'circle');
  lens.setAttribute('cx','10.5');lens.setAttribute('cy','10.5');lens.setAttribute('r','6.5');
  const handle=document.createElementNS(ns,'line');
  handle.setAttribute('x1','15.5');handle.setAttribute('y1','15.5');
  handle.setAttribute('x2','20.5');handle.setAttribute('y2','20.5');
  svg.append(lens,handle);
  return svg;
}

function _convNormPath(p){return (p||'').replace(/\\/g,'/').replace(/^\//,'');}
function _convIsWatermarkReviewed(source){return !!(source&&S.convWatermarkReviewed&&S.convWatermarkReviewed[source]);}
function _convWatermarkMatchList(source){
  return Object.keys((S.convWatermarkMatches&&S.convWatermarkMatches[source])||{});
}
function _convRemoveWatermark(source,relPath){
  const rel=_convNormPath(relPath);
  if(!source||!rel)return;
  const sourceMatches={...((S.convWatermarkMatches&&S.convWatermarkMatches[source])||{})};
  delete sourceMatches[rel];
  S.convWatermarkMatches={...(S.convWatermarkMatches||{}),[source]:sourceMatches};
  S.convWatermarkReviewed={...(S.convWatermarkReviewed||{}),[source]:true};
  _invalidateCropCaches();
  sessionStorage.setItem('mcs_convWatermarkReviewed',JSON.stringify(S.convWatermarkReviewed));
  sessionStorage.setItem('mcs_convWatermarkMatches',JSON.stringify(S.convWatermarkMatches));
  _convSaveSidecarForSource(source);render();
}
function _convSourceKey(source){return (source||'').replace(/\\/g,'/').replace(/\/+$/,'');}
function _convEnsureSuppressed(source){
  const k=_convSourceKey(source);
  if(!k)return null;
  if(!S.convAutoBmSuppressed[k]||typeof S.convAutoBmSuppressed[k]!=='object')S.convAutoBmSuppressed[k]={};
  return S.convAutoBmSuppressed[k];
}
function _convIsAutoBmSuppressed(source, relPath){
  const k=_convSourceKey(source);
  const rp=_convNormPath(relPath);
  return !!(k&&rp&&S.convAutoBmSuppressed[k]&&S.convAutoBmSuppressed[k][rp]);
}
function _convSetAutoBmSuppressed(source, relPath, on){
  const rp=_convNormPath(relPath);
  const map=_convEnsureSuppressed(source);
  if(!map||!rp)return;
  if(on) map[rp]=true;
  else delete map[rp];
}
function _convSetBookmark(relPath, name, source){
  const rp=_convNormPath(relPath);
  const nm=(name||'').trim();
  if(!rp)return;
  if(!nm){ _convDeleteBookmark(rp, source, true); return; }
  _convDemoteAutoBookmarksInFolder(source, rp);
  S.convBookmarks[rp]=nm;
  S.convBookmarkOrigin[rp]='manual';
  if(source) _convSetAutoBmSuppressed(source, rp, false);
}
function _convDeleteBookmark(relPath, source, suppressAuto){
  const rp=_convNormPath(relPath);
  if(!rp)return;
  delete S.convBookmarks[rp];
  delete S.convBookmarkOrigin[rp];
  if(suppressAuto&&source) _convSetAutoBmSuppressed(source, rp, true);
}
function _convSetBookmarkWithOrigin(relPath, name, source, origin){
  _convSetBookmark(relPath, name, source);
  const rp=_convNormPath(relPath);
  if(rp && (origin==='auto' || origin==='manual')) S.convBookmarkOrigin[rp]=origin;
}
function _convBookmarkOriginOf(relPath){
  const rp=_convNormPath(relPath);
  return S.convBookmarkOrigin[rp]||'manual';
}
function _convBookmarkOriginExists(relPath){
  const rp=_convNormPath(relPath);
  return Object.prototype.hasOwnProperty.call(S.convBookmarkOrigin||{}, rp);
}
function _convFilesForSource(source){
  if(!source||!S.convScanned)return [];
  if(S.convScanned[source])return S.convScanned[source]||[];
  const sk=_convSourceKey(source);
  const hit=Object.keys(S.convScanned).find(k=>_convSourceKey(k)===sk);
  return hit ? (S.convScanned[hit]||[]) : [];
}
function _convDemoteAutoBookmarksInFolder(source, relPath){
  const rp=_convNormPath(relPath);
  if(!source||!rp)return;
  const files=_convFilesForSource(source);
  const cur=files.find(f=>_convNormPath(f.relPath)===rp);
  if(!cur)return;
  const folder=cur.folder||'';
  files.forEach(f=>{
    const frp=_convNormPath(f.relPath);
    if(!frp||frp===rp||(f.folder||'')!==folder)return;
    if(S.convBookmarks[frp]&&_convBookmarkOriginOf(frp)==='auto'){
      _convDeleteBookmark(frp, source, true);
    }
  });
}
function _convFirstRelByFolder(files){
  const firstRelByFolder={};
  (files||[]).forEach(f=>{
    const folder=f.folder||'';
    if(!(folder in firstRelByFolder)) firstRelByFolder[folder]=_convNormPath(f.relPath);
  });
  return firstRelByFolder;
}
function _convBuildAutoFolderBookmarks(files, source){
  const firstByFolder={};
  (files||[]).forEach(f=>{
    const folder=f.folder||'';
    if(!folder)return;
    if(!(folder in firstByFolder)) firstByFolder[folder]=f.relPath;
  });
  const out=[];
  Object.entries(firstByFolder).forEach(([folder, relPath])=>{
    if(_convIsAutoBmSuppressed(source, relPath)) return;
    const guessed=convGuessChapterName(folder);
    if(guessed) out.push({relPath: _convNormPath(relPath), name: guessed});
  });
  return out;
}

function _getActiveConvProfileInfo(){
  let info=null;
  if(S.convProfiles){
    Object.values(S.convProfiles).forEach(g=>{if(g[S.convProfile])info=g[S.convProfile];});
  }
  return info;
}
function _convBuildPreviewRequest(file){
  const pinfo=_getActiveConvProfileInfo();
  const pw=pinfo&&Number.isFinite(Number(pinfo.width))?parseInt(pinfo.width,10):0;
  const ph=pinfo&&Number.isFinite(Number(pinfo.height))?parseInt(pinfo.height,10):0;
  const editOps=(file&&file.relPath&&Array.isArray(S.convEditOps[file.relPath]))?S.convEditOps[file.relPath]:[];
  const noCrop=!!(file&&file.relPath&&S.convExclusions[file.relPath]&&S.convExclusions[file.relPath]['no-crop']);
  const customCrop=!!(file&&file.relPath&&S.convCustomCrop[file.relPath]);
  const native=_isNativeFormat(S.convFormat);
  return {
    path:file.path,
    power:native?1.0:parseFloat(S.convCroppingPower)||1.0,
    mode:native?0:parseInt(S.convCropping)||0,
    maic_crop:!!S.convMaicCrop&&!noCrop&&!customCrop,
    maic_margin_pct:Math.max(0,Math.min(10,parseFloat(S.convMaicMarginPct)||0)),
    maic_watermarks:!!S.convMaicWatermarks,
    maic_watermark_page_enabled:(!_convIsWatermarkReviewed(S.convExpandedSource||S.convSources[0]||'')||
      _convWatermarkMatchList(S.convExpandedSource||S.convSources[0]||'').includes(_convNormPath(file&&file.relPath))),
    watermark_revision:S._convWatermarkRevision||'0',
    maic_page_numbers:!!S.convMaicPageNumbers,
    page_number_scope:_convPageNumberScope(),
    minimum_page_number:S.convMaicPageNumbers?_convPageNumberMinimum(file,_convPageNumberScope()):1,
    page_number_memory_revision:S._convPageNumberMemoryRevision||'0',
    cleanup_method:S.cleanMethod||'lama',
    cleanup_padding:parseInt(S.maskPadding)||0,
    preserve_margin_h:native?0:parseInt(S.convPreserveMarginH)||0,
    preserve_margin_v:native?0:parseInt(S.convPreserveMarginV)||0,
    inter_panel_crop:native?0:parseInt(S.convInterPanelCrop)||0,
    borders_color:S.convBordersColor||'none',
    webtoon:!native&&!!S.convWebtoon,
    no_processing:!!S.convNoProcessing,
    preview_variant:'auto',
    splitter:_convEffectiveSplitter(),
    no_rotate:!!S.convNoRotate,
    native,
    rotate_first:!native&&!!S.convRotateFirst,
    manga_mode:!!S.convManga,
    profile_width:pw,
    profile_height:ph,
    edit_ops:editOps
  };
}
function _convUsesFinalPreview(){
  return S.convPreviewMode==='final'&&_isNativeFormat(S.convFormat)&&
    !S._convEditMode&&!S._convFolioMode&&!S._convWatermarkCapture;
}
function _convBuildFinalPreviewRequest(file){
  const req=_convBuildPreviewRequest(file);
  const extra=S.convExtraMargin[file.relPath];
  return {...req,
    hq:!String(S.convFormat).toUpperCase().startsWith('KFX')&&!!S.convHQ,
    no_padding:!!S.convKfxNoPadding,
    force_color:!!S.convForceColor,
    is_cover:/^cover\.[^.]+$/i.test(file.relPath||''),
    spread_preview_mode:parseInt(S.convSpreadPreviewMode)||0,
    custom_crop:S.convCustomCrop[file.relPath]||null,
    custom_split:S.convCustomSplit[file.relPath]||null,
    extra_margin:extra?{...extra,color:extra.color||S._convExtraMarginColor}:null
  };
}
async function _drawFinalPreview(container,file){
  const status=h('div',{role:'status',style:{color:'var(--text3)',fontSize:'0.8rem'}},t('conv.preview_loading','Rendering preview…'));
  container.append(status);
  try{
    const response=await apiPost('/api/convert/final-preview',_convBuildFinalPreviewRequest(file));
    const result=await response.json();
    if(!container.isConnected)return;
    if(!response.ok||!result.ok)throw new Error(result.error||'Preview failed');
    status.remove();
    const stage=h('div',{style:{display:'flex',flexDirection:S.convManga?'row-reverse':'row',gap:'4px',
      alignItems:'center',justifyContent:'center',height:'98%',maxWidth:'98%',minWidth:'0',
      transformOrigin:'center center'}});
    const sync=()=>{stage.style.transform=`translate(${S.convViewX}px,${S.convViewY}px) scale(${S.convViewScale})`;};
    sync();
    result.pages.forEach(page=>stage.append(h('img',{src:page.url,alt:t('conv.preview_final','Final image'),
      title:`${page.width} × ${page.height}`,style:{display:'block',maxHeight:'100%',
        maxWidth:(100/result.pages.length)+'%',width:'auto',height:'auto',objectFit:'contain'}})));
    container.append(stage);
    container.addEventListener('wheel',e=>{e.preventDefault();S.convViewScale=Math.max(0.5,Math.min(10,S.convViewScale*(e.deltaY<0?1.15:1/1.15)));sync();},{passive:false});
    let drag=null;
    stage.addEventListener('pointerdown',e=>{if(e.button!==0)return;e.preventDefault();drag={x:e.clientX,y:e.clientY};stage.setPointerCapture(e.pointerId);});
    stage.addEventListener('pointermove',e=>{if(!drag)return;S.convViewX+=e.clientX-drag.x;S.convViewY+=e.clientY-drag.y;drag={x:e.clientX,y:e.clientY};sync();});
    const end=()=>{drag=null;};stage.addEventListener('pointerup',end);stage.addEventListener('pointercancel',end);
  }catch(error){if(container.isConnected)status.textContent=t('conv.preview_failed','Preview failed')+': '+error.message;}
}
function _convBuildDisplayPreviewRequest(req,{captureMode=false,fullImageView=false,outputOrder=[]}={}){
  if(!req)return null;
  if(captureMode)return {
    ...req,preview_variant:'N',splitter:0,no_rotate:true,rotate_first:false,
    maic_page_numbers:false,maic_crop:false,maic_watermarks:false
  };
  // Before crop metadata arrives, AUTO can return just S1. Show the whole
  // source so both sides are visible while folio/crop analysis is running.
  // The paired viewer reuses this same N image when its layout is ready.
  if(fullImageView||!outputOrder.length)return {...req,preview_variant:'N'};
  return req;
}
function _convBuildUnifiedCropRequest(baseReq){
  if(!baseReq)return null;
  return {
    ...baseReq,
    splitter:0,
    no_rotate:true,
    rotate_first:false,
    preview_variant:'N'
  };
}
function _convPreviewCacheKey(req){
  return [
    req.path,req.power,req.mode,req.maic_crop?1:0,req.maic_margin_pct,req.maic_watermarks?1:0,req.maic_watermark_page_enabled?1:0,req.watermark_revision||'0',req.maic_page_numbers?1:0,req.page_number_scope||'',req.page_number_memory_revision||'0',req.minimum_page_number||1,req.cleanup_method,req.cleanup_padding,req.preserve_margin_h,req.preserve_margin_v,req.inter_panel_crop,req.borders_color,
    req.webtoon?1:0,req.no_processing?1:0,req.preview_variant,req.splitter,req.no_rotate?1:0,
    req.native?1:0,
    req.rotate_first?1:0,req.manga_mode?1:0,req.profile_width,req.profile_height,JSON.stringify(req.edit_ops||[])
  ].join('|');
}
// Keep recent metadata across navigation and share an in-flight calculation
// across renders. Options and teaching revisions are part of the key; the TTL
// also bounds staleness when source images are modified outside the app.
const _convCropRequests=new Map();
function _convFetchCropPreview(req){
  const key=_convPreviewCacheKey(req);
  const cached=_convCropRequests.get(key);
  if(cached&&cached.expires>Date.now()){
    _convCropRequests.delete(key);_convCropRequests.set(key,cached);
    return cached.promise;
  }
  const entry={expires:Infinity,promise:null};
  entry.promise=(async()=>{
    try{
      const response=await apiPost('/api/convert/crop-preview',req);
      const result=await response.json();
      if(response.ok&&result.ok){
        entry.expires=Date.now()+30000;
        if(req.maic_page_numbers&&result.maic_page_number_decision&&_convCropRequests.get(key)===entry&&
          _convRecordPageNumbers(req.path,result.maic_page_number_decision))_convUpdatePageNumberBadges(req.page_number_scope);
      }
      else if(_convCropRequests.get(key)===entry)_convCropRequests.delete(key);
      return result;
    }catch(error){
      if(_convCropRequests.get(key)===entry)_convCropRequests.delete(key);
      throw error;
    }
  })();
  _convCropRequests.set(key,entry);
  while(_convCropRequests.size>32)_convCropRequests.delete(_convCropRequests.keys().next().value);
  return entry.promise;
}
function _convBindPageNumberPreview(container,request,apply){
  container._pageNumberPreviewKey=_convPreviewCacheKey(request);
  container._refreshPageNumbers=async scope=>{
    if(!container.isConnected||scope!==request.page_number_scope||!request.maic_page_numbers)return;
    const file=((S.convScanned||{})[scope]||[]).find(file=>file.path===request.path);
    if(!file)return;
    const next={...request,minimum_page_number:_convPageNumberMinimum(file,scope)};
    const key=_convPreviewCacheKey(next);
    if(key===container._pageNumberPreviewKey)return;
    container._pageNumberPreviewKey=key;
    try{
      const result=await _convFetchCropPreview(next);
      if(container.isConnected&&container._pageNumberPreviewKey===key&&result.ok)apply(result,next);
    }catch(error){console.warn('crop-preview refresh error:',error);}
  };
}
function _isWideSidebarThumb(width,height){
  return Number(width||0)>Number(height||0)*1.25;
}
function _convThumbUrl(file,req){
  const qp=new URLSearchParams({
    full:'1',
    path:file.path,
    preview_variant:req.preview_variant,
    splitter:String(req.splitter),
    no_rotate:req.no_rotate?'1':'0',
    native:req.native?'1':'0',
    rotate_first:req.rotate_first?'1':'0',
    manga_mode:req.manga_mode?'1':'0',
    webtoon:req.webtoon?'1':'0',
    no_processing:req.no_processing?'1':'0',
    profile_width:String(req.profile_width||0),
    profile_height:String(req.profile_height||0),
    maic_crop:req.maic_crop?'1':'0',
    maic_watermarks:req.maic_watermarks?'1':'0',
    maic_watermark_page_enabled:req.maic_watermark_page_enabled?'1':'0',
    maic_page_numbers:req.maic_page_numbers?'1':'0',
    page_number_scope:req.page_number_scope||'',
    minimum_page_number:String(req.minimum_page_number||1),
    page_number_memory_revision:req.page_number_memory_revision||'0',
    cleanup_method:req.cleanup_method||'lama',
    cleanup_padding:String(req.cleanup_padding||0),
    // The Crop preview marks a found watermark or folio with a mask over the
    // original page; only the Final image (a separate endpoint) erases it.
    erase_artifacts:'0'
  });
  if((req.maic_crop||req.maic_watermarks||req.maic_page_numbers)&&Array.isArray(req.edit_ops)&&req.edit_ops.length){
    qp.set('edit_ops',JSON.stringify(req.edit_ops));
  }
  return API+'/api/convert/serve-thumb?'+qp.toString();
}

function _convExtractHalfOrder(modes){
  const out=[];
  (Array.isArray(modes)?modes:[]).forEach(v=>{
    const code=String(v||'').toUpperCase();
    if(code==='S1'||code==='S2'||code==='R')out.push(code);
  });
  return out;
}
function _convGetSplitOrderForFile(file){
  if(!file)return [];
  const rel=_convNormPath(file.relPath);
  if(!rel)return [];
  const byRel=S._convSplitOrderByRel||(S._convSplitOrderByRel={});
  if(Array.isArray(byRel[rel])&&byRel[rel].length)return byRel[rel].slice();
  const req=_convBuildPreviewRequest(file);
  const key=_convPreviewCacheKey(req);
  const data=(S._cropCache&&S._cropCache.key===key)?S._cropCache.data:null;
  const order=_convExtractHalfOrder(data&&Array.isArray(data.output_variants)?data.output_variants:[]);
  if(order.length)byRel[rel]=order.slice();
  return order;
}
const _CONV_PAIR_HEIGHT_FRAC=1;
const _CONV_PAIR_GAP_PX=6;
function _convPairHasRoomByMargins(){
  const ca=document.querySelector('.canvas-area');
  const pair=document.querySelector('.conv-pair-stage');
  if(!ca||!pair)return null;
  const imgs=Array.from(pair.querySelectorAll('img.main-canvas')).filter(img=>img&&img.isConnected&&img.naturalWidth>0&&img.naturalHeight>0);
  if(imgs.length<2)return null;
  const cr=ca.getBoundingClientRect();
  let l=Infinity,r=-Infinity,t=Infinity,b=-Infinity;
  imgs.forEach(img=>{
    const ir=img.getBoundingClientRect();
    l=Math.min(l,ir.left);r=Math.max(r,ir.right);t=Math.min(t,ir.top);b=Math.max(b,ir.bottom);
  });
  if(!Number.isFinite(l)||!Number.isFinite(r)||!Number.isFinite(t)||!Number.isFinite(b))return null;
  const sideInset=Math.max(0,Math.min(l-cr.left,cr.right-r));
  const verticalInset=Math.max(0,Math.min(t-cr.top,cr.bottom-b));
  return sideInset+0.5>=verticalInset;
}
function _convCanShowSplitPairForOrder(order,file){
  const splitMode=_convEffectiveSplitter();
  if(splitMode===1)return false;
  const hasPair=Array.isArray(order)&&order.includes('S1')&&order.includes('S2');
  const sel=String(S.convPreviewVariant||'auto').toUpperCase();
  if(!hasPair||!(sel==='AUTO'||sel==='S1'||sel==='S2'))return false;
  if(file){
    const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
    const cur=(Array.isArray(sc)&&S.convViewIdx!==null&&S.convViewIdx>=0&&S.convViewIdx<sc.length)?sc[S.convViewIdx]:null;
    if(cur&&cur.path===file.path){
      const keepByMargins=_convPairHasRoomByMargins();
      if(keepByMargins===true)return true;
    }
  }
  const pinfo=_getActiveConvProfileInfo();
  const pw=pinfo&&Number.isFinite(Number(pinfo.width))?Math.max(1,parseInt(pinfo.width,10)):1;
  const ph=pinfo&&Number.isFinite(Number(pinfo.height))?Math.max(1,parseInt(pinfo.height,10)):1;
  const ratio=pw/Math.max(1,ph);
  const cw=Math.max(0,parseInt(S._convCanvasW||0,10)||0);
  const ch=Math.max(0,parseInt(S._convCanvasH||0,10)||0);
  const vw=cw>0?cw:Math.max(640,Math.floor(window.innerWidth*0.7));
  const vh=ch>0?ch:Math.max(360,Math.floor(window.innerHeight*0.6));
  const fitFrac=0.98;
  const targetH=vh*_CONV_PAIR_HEIGHT_FRAC;
  const frameW=targetH*ratio;
  const stageW=(frameW*2)+_CONV_PAIR_GAP_PX;
  const topInset=((1-fitFrac)*0.5)*targetH;
  const outerInset=((1-fitFrac)*0.5)*frameW;
  const needCanvasSide=Math.max(0,topInset-outerInset);
  const needCanvasW=stageW+(needCanvasSide*2);
  const visibleHalfW=frameW*fitFrac;
  const minHalfW=170;
  return (visibleHalfW>=minHalfW)&&(vw>=needCanvasW);
}
function _convGetPairRange(order,step){
  if(!Array.isArray(order)||order.length===0||step<0||step>=order.length)return null;
  const isSplit=v=>v==='S1'||v==='S2';
  if(!isSplit(order[step]))return null;
  let s=step,e=step;
  while(s-1>=0&&isSplit(order[s-1]))s--;
  while(e+1<order.length&&isSplit(order[e+1]))e++;
  const seg=order.slice(s,e+1);
  if(!(seg.includes('S1')&&seg.includes('S2')))return null;
  return {start:s,end:e};
}
function _convGetSplitStep(relPath,maxLen){
  const rel=_convNormPath(relPath);
  if(!rel||!maxLen||maxLen<1)return 0;
  const byRel=S._convSplitStepByRel||(S._convSplitStepByRel={});
  const raw=parseInt(byRel[rel],10);
  const step=Number.isFinite(raw)?raw:0;
  return Math.max(0,Math.min(maxLen-1,step));
}
function _convSetSplitStep(relPath,step){
  const rel=_convNormPath(relPath);
  if(!rel)return;
  const byRel=S._convSplitStepByRel||(S._convSplitStepByRel={});
  byRel[rel]=Math.max(0,parseInt(step,10)||0);
}
function _convNavigatePreview(dir){
  if(S.tab!=='convert'||S.convViewIdx===null)return false;
  if(dir!==-1&&dir!==1)return false;
  const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
  if(!Array.isArray(sc)||S.convViewIdx<0||S.convViewIdx>=sc.length)return false;
  const idx=S.convViewIdx;
  const cur=sc[idx];
  if(!cur)return false;
  if(_convUsesFinalPreview()){
    const next=idx+dir;
    if(next<0||next>=sc.length)return false;
    S.convViewIdx=next;convResetView();render();return true;
  }
  const autoSel=String(S.convPreviewVariant||'auto').toLowerCase()==='auto';
  const splitPairMode=_convEffectiveSplitter()!==1;
  const curOrder=_convGetSplitOrderForFile(cur);
  const stepMode=splitPairMode&&autoSel&&curOrder.length>1;
  const curStep=stepMode?_convGetSplitStep(cur.relPath,curOrder.length):0;
  const curPairRange=(stepMode&&_convCanShowSplitPairForOrder(curOrder,cur))?_convGetPairRange(curOrder,curStep):null;

  if(dir>0){
    if(stepMode&&curPairRange&&curPairRange.end<curOrder.length-1){
      convResetView();
      _convSetSplitStep(cur.relPath,curPairRange.end+1);
      S._convNavByKey=true;
      render();
      return true;
    }
    if(stepMode&&!curPairRange&&curStep<curOrder.length-1){
      convResetView();
      _convSetSplitStep(cur.relPath,curStep+1);
      S._convNavByKey=true;
      render();
      return true;
    }
    if(idx<sc.length-1){
      const next=sc[idx+1];
      convResetView();
      S.convViewIdx=idx+1;
      if(next)_convSetSplitStep(next.relPath,0);
      S._convNavByKey=true;
      render();
      return true;
    }
    return false;
  }

  if(stepMode&&curPairRange&&curPairRange.start>0){
    convResetView();
    _convSetSplitStep(cur.relPath,curPairRange.start-1);
    S._convNavByKey=true;
    render();
    return true;
  }
  if(stepMode&&!curPairRange&&curStep>0){
    const prevStep=curStep-1;
    const prevPairRange=(stepMode&&_convCanShowSplitPairForOrder(curOrder,cur))?_convGetPairRange(curOrder,prevStep):null;
    convResetView();
    _convSetSplitStep(cur.relPath,prevPairRange?prevPairRange.start:prevStep);
    S._convNavByKey=true;
    render();
    return true;
  }
  if(idx>0){
    const prev=sc[idx-1];
    convResetView();
    S.convViewIdx=idx-1;
    if(prev){
      const prevOrder=_convGetSplitOrderForFile(prev);
      const prevStepMode=splitPairMode&&autoSel&&prevOrder.length>1;
      if(prevStepMode)_convSetSplitStep(prev.relPath,prevOrder.length-1);
    }
    S._convNavByKey=true;
    render();
    return true;
  }
  return false;
}

function _getExtraMarginFillColor(relPath){
  if(relPath){const em=S.convExtraMargin[relPath];if(em&&em.color)return em.color;}
  return S._convExtraMarginColor||'#ffffff';
}
function _applyExtraMarginFrame(img,relPath,syncWrapFn){
  // Expand canvas with fill-colored margins (used for no-crop / excluded images where crop overlay is absent)
  if(img._emApplied)return;
  const em=S.convExtraMargin[relPath];
  if(!em)return;
  const natW=img.naturalWidth||1;
  const natH=img.naturalHeight||1;
  const mT=em.top||0,mB=em.bottom||0,mL=em.left||0,mR=em.right||0;
  if(!mT&&!mB&&!mL&&!mR)return;
  const totalW=natW+mL+mR;
  const totalH=natH+mT+mB;
  const canvas=document.createElement('canvas');
  canvas.width=totalW;
  canvas.height=totalH;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle=_getExtraMarginFillColor(relPath);
  ctx.fillRect(0,0,totalW,totalH);
  ctx.drawImage(img,mL,mT,natW,natH);
  ctx.strokeStyle='rgba(34,197,94,0.5)';
  ctx.lineWidth=2;
  ctx.setLineDash([6,4]);
  ctx.strokeRect(mL+1,mT+1,natW-2,natH-2);
  img._emApplied=true;
  img.src=canvas.toDataURL('image/png');
  if(syncWrapFn){
    img.addEventListener('load',()=>{requestAnimationFrame(syncWrapFn);},{once:true});
  }
}

function _replayEditOps(ctx,ops){
  if(!ops||!ops.length)return;
  ops.forEach(op=>{
    ctx.fillStyle=op.color||'#fff';
    ctx.strokeStyle=op.color||'#fff';
    if(op.type==='rect'){
      ctx.fillRect(op.x,op.y,op.w,op.h);
    } else if(op.type==='brush'&&op.points&&op.points.length>0){
      ctx.lineWidth=op.size||20;
      ctx.lineCap='round';
      ctx.lineJoin='round';
      if(op.points.length===1){
        ctx.beginPath();
        ctx.arc(op.points[0][0],op.points[0][1],(op.size||20)/2,0,Math.PI*2);
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.moveTo(op.points[0][0],op.points[0][1]);
        for(let i=1;i<op.points.length;i++)ctx.lineTo(op.points[i][0],op.points[i][1]);
        ctx.stroke();
      }
    }
  });
}
function _applyEditOps(img,relPath,syncWrapFn){
  if(img._editOpsApplied)return;
  const ops=S.convEditOps[relPath];
  if(!ops||!ops.length)return;
  const natW=img.naturalWidth||1;
  const natH=img.naturalHeight||1;
  const canvas=document.createElement('canvas');
  canvas.width=natW;canvas.height=natH;
  const ctx=canvas.getContext('2d');
  ctx.drawImage(img,0,0,natW,natH);
  _replayEditOps(ctx,ops);
  img._editOpsApplied=true;
  img.src=canvas.toDataURL('image/png');
  if(syncWrapFn)img.addEventListener('load',()=>{requestAnimationFrame(syncWrapFn);},{once:true});
}

function _drawPageNumberRemovalMasks(container,cropData,sourceRegion){
  const old=container.querySelector('.page-number-removal-overlay');if(old)old.remove();
  if(!cropData||!container)return false;
  let boxes=Array.isArray(cropData.maic_page_number_preview_boxes)?cropData.maic_page_number_preview_boxes:[];
  let refW=Math.max(1,parseInt(cropData.width,10)||1);
  let refH=Math.max(1,parseInt(cropData.height,10)||1);
  if(sourceRegion){
    const decision=cropData.maic_page_number_decision||{};
    boxes=Array.isArray(decision.boxes)?decision.boxes:[];
    refW=Math.max(1,parseInt(sourceRegion.w,10)||1);
    refH=Math.max(1,parseInt(sourceRegion.h,10)||1);
    boxes=boxes.map(box=>{
      if(!Array.isArray(box)||box.length!==4)return null;
      const x1=Math.max(Number(box[0]),Number(sourceRegion.x0));
      const y1=Math.max(Number(box[1]),Number(sourceRegion.y0));
      const x2=Math.min(Number(box[2]),Number(sourceRegion.x0)+refW);
      const y2=Math.min(Number(box[3]),Number(sourceRegion.y0)+refH);
      if(!(x2>x1&&y2>y1))return null;
      return [x1-Number(sourceRegion.x0),y1-Number(sourceRegion.y0),x2-Number(sourceRegion.x0),y2-Number(sourceRegion.y0)];
    }).filter(Boolean);
  }
  if(!boxes.length)return false;
  const overlay=h('div',{className:'page-number-removal-overlay',style:{position:'absolute',inset:'0',
    pointerEvents:'none',overflow:'hidden',zIndex:'14'}});
  boxes.forEach(box=>{
    if(!Array.isArray(box)||box.length!==4)return;
    const x1=Math.max(0,Math.min(refW,Number(box[0]))),y1=Math.max(0,Math.min(refH,Number(box[1])));
    const x2=Math.max(x1,Math.min(refW,Number(box[2]))),y2=Math.max(y1,Math.min(refH,Number(box[3])));
    if(!(x2>x1&&y2>y1))return;
    overlay.append(h('div',{style:{position:'absolute',left:(x1/refW*100)+'%',top:(y1/refH*100)+'%',
      width:((x2-x1)/refW*100)+'%',height:((y2-y1)/refH*100)+'%',minWidth:'4px',minHeight:'4px',
      background:'rgba(245,158,11,0.38)',border:'1.5px dashed rgba(251,191,36,0.95)',
      borderRadius:'2px',boxSizing:'border-box'}}));
  });
  if(!overlay.childNodes.length)return false;
  container.append(overlay);return true;
}

function _drawWatermarkRemovalMasks(container,cropData,sourceRegion){
  const old=container.querySelector('.watermark-removal-overlay');if(old)old.remove();
  if(!cropData||!container)return false;
  let matches=Array.isArray(cropData.maic_watermark_preview_matches)?cropData.maic_watermark_preview_matches:[];
  let boxes=matches.map(match=>match&&match.box).filter(Boolean);
  let refW=Math.max(1,parseInt(cropData.width,10)||1);
  let refH=Math.max(1,parseInt(cropData.height,10)||1);
  if(sourceRegion){
    matches=Array.isArray(cropData.maic_watermark_matches)?cropData.maic_watermark_matches:[];
    boxes=matches.map(match=>match&&match.box).filter(Boolean);
    refW=Math.max(1,parseInt(sourceRegion.w,10)||1);
    refH=Math.max(1,parseInt(sourceRegion.h,10)||1);
    boxes=boxes.map(box=>{
      if(!Array.isArray(box)||box.length!==4)return null;
      const x1=Math.max(Number(box[0]),Number(sourceRegion.x0));
      const y1=Math.max(Number(box[1]),Number(sourceRegion.y0));
      const x2=Math.min(Number(box[2]),Number(sourceRegion.x0)+refW);
      const y2=Math.min(Number(box[3]),Number(sourceRegion.y0)+refH);
      if(!(x2>x1&&y2>y1))return null;
      return [x1-Number(sourceRegion.x0),y1-Number(sourceRegion.y0),x2-Number(sourceRegion.x0),y2-Number(sourceRegion.y0)];
    }).filter(Boolean);
  }
  if(!boxes.length)return false;
  const overlay=h('div',{className:'watermark-removal-overlay',style:{position:'absolute',inset:'0',
    pointerEvents:'none',overflow:'hidden',zIndex:'15'}});
  boxes.forEach(box=>{
    if(!Array.isArray(box)||box.length!==4)return;
    const x1=Math.max(0,Math.min(refW,Number(box[0]))),y1=Math.max(0,Math.min(refH,Number(box[1])));
    const x2=Math.max(x1,Math.min(refW,Number(box[2]))),y2=Math.max(y1,Math.min(refH,Number(box[3])));
    if(!(x2>x1&&y2>y1))return;
    overlay.append(h('div',{style:{position:'absolute',left:(x1/refW*100)+'%',top:(y1/refH*100)+'%',
      width:((x2-x1)/refW*100)+'%',height:((y2-y1)/refH*100)+'%',minWidth:'4px',minHeight:'4px',
      background:'repeating-linear-gradient(135deg,rgba(250,204,21,0.34) 0 5px,rgba(234,179,8,0.14) 5px 10px)',
      border:'1.5px dashed rgba(250,204,21,0.98)',borderRadius:'2px',boxSizing:'border-box'}}));
  });
  if(!overlay.childNodes.length)return false;
  container.append(overlay);return true;
}

function _drawCropOverlay(container,imgEl,cropData,relPath){
  const old2=container.querySelector('.crop-overlay-wrap');if(old2)old2.remove();
  const {width:natW,height:natH,crop}=cropData;
  const previewVariant=String((cropData&&cropData.preview_variant)||'N').toUpperCase();
  const canEdit=!!relPath&&previewVariant==='N';

  // Use editable crop bounds - init from custom crops if exists, else from detected
  const cropKey=natW+'x'+natH+'|'+(relPath||'')+'|'+previewVariant;
  if(!S._editCrop||S._editCropKey!==cropKey){
    const custom=canEdit&&relPath?S.convCustomCrop[relPath]:null;
    if(canEdit&&custom&&custom.width===natW&&custom.height===natH){
      S._editCrop={top:custom.top,bottom:custom.bottom,left:custom.left,right:custom.right};
    } else {
      S._editCrop={...crop};
    }
    S._editCropKey=cropKey;
  }
  const ec=S._editCrop;
  const origCrop=crop;
  const isCustom=canEdit&&(ec.top!==origCrop.top||ec.bottom!==origCrop.bottom||ec.left!==origCrop.left||ec.right!==origCrop.right);
  const inter=(cropData&&cropData.inter_panel)||{};
  const interRows=Array.isArray(inter.rows)?inter.rows:[];
  const interCols=Array.isArray(inter.cols)?inter.cols:[];

  // Extra margin data — margin strips go OUTSIDE crop boundary, pushing mask outward
  const _em=relPath?S.convExtraMargin[relPath]:null;
  const _emT=_em?(_em.top||0):0,_emB=_em?(_em.bottom||0):0,_emL=_em?(_em.left||0):0,_emR=_em?(_em.right||0):0;
  // Crop boundary positions (for dashed line, handles, inter-panel)
  const tPct=(ec.top/natH*100).toFixed(3);
  const bPct=((natH-1-ec.bottom)/natH*100).toFixed(3);
  const lPct=(ec.left/natW*100).toFixed(3);
  const rPct=((natW-1-ec.right)/natW*100).toFixed(3);
  // Mask positions — pushed outward by margin amounts (can go negative = beyond image edge)
  const maskTPx=ec.top-_emT, maskBPx=(natH-1-ec.bottom)-_emB, maskLPx=ec.left-_emL, maskRPx=(natW-1-ec.right)-_emR;
  // Unclamped percentages (may be negative when margin extends beyond image)
  const maskTPct=(maskTPx/natH*100).toFixed(3);
  const maskBPct=(maskBPx/natH*100).toFixed(3);
  const maskLPct=(maskLPx/natW*100).toFixed(3);
  const maskRPct=(maskRPx/natW*100).toFixed(3);
  // Overflow amounts (margin extends beyond image edge, in %)
  const ovfTPct=maskTPx<0?(-maskTPx/natH*100).toFixed(3):'0';
  const ovfBPct=maskBPx<0?(-maskBPx/natH*100).toFixed(3):'0';
  const ovfLPct=maskLPx<0?(-maskLPx/natW*100).toFixed(3):'0';
  const ovfRPct=maskRPx<0?(-maskRPx/natW*100).toFixed(3):'0';

  const wrap=h('div',{className:'crop-overlay-wrap',style:{position:'absolute',top:'-'+ovfTPct+'%',left:'-'+ovfLPct+'%',
    width:(100+parseFloat(ovfLPct)+parseFloat(ovfRPct))+'%',height:(100+parseFloat(ovfTPct)+parseFloat(ovfBPct))+'%',
    pointerEvents:'none',overflow:'visible'}});
  // Inner reference: percentages inside wrap now account for overflow
  const wPctW=100+parseFloat(ovfLPct)+parseFloat(ovfRPct);
  const wPctH=100+parseFloat(ovfTPct)+parseFloat(ovfBPct);
  // Remap: image-relative % -> wrap-relative %
  const _rx=v=>(parseFloat(ovfLPct)+parseFloat(v))/wPctW*100;
  const _ry=v=>(parseFloat(ovfTPct)+parseFloat(v))/wPctH*100;
  const _rw=v=>parseFloat(v)/wPctW*100;
  const _rh=v=>parseFloat(v)/wPctH*100;
  const mc=isCustom?'rgba(100,150,255,0.22)':'rgba(255,50,50,0.22)';
  const bc=isCustom?'rgba(100,150,255,0.6)':'rgba(255,120,80,0.6)';

  // Masks: top/bottom/left/right dark overlays covering area outside crop+margin
  // Top mask: from wrap top (0) to mask line
  const mTy=_ry(maskTPct);
  const mBy=_ry(String(100-parseFloat(maskBPct)));
  const mLx=_rx(maskLPct);
  const mRx=_rx(String(100-parseFloat(maskRPct)));
  wrap.append(h('div',{style:{position:'absolute',top:'0',left:'0',width:'100%',height:mTy+'%',background:mc}}));
  wrap.append(h('div',{style:{position:'absolute',bottom:'0',left:'0',width:'100%',height:(100-mBy)+'%',background:mc}}));
  wrap.append(h('div',{style:{position:'absolute',top:mTy+'%',left:'0',width:mLx+'%',height:(mBy-mTy)+'%',background:mc}}));
  wrap.append(h('div',{style:{position:'absolute',top:mTy+'%',right:'0',width:(100-mRx)+'%',height:(mBy-mTy)+'%',background:mc}}));
  // Crop boundary dashed line at original position (image-relative -> wrap-relative)
  const cropT=_ry(tPct),cropL=_rx(lPct),cropB=_ry(String(100-parseFloat(bPct))),cropR=_rx(String(100-parseFloat(rPct)));
  wrap.append(h('div',{style:{position:'absolute',top:cropT+'%',left:cropL+'%',width:(cropR-cropL)+'%',height:(cropB-cropT)+'%',
    border:'1.5px dashed '+bc,boxSizing:'border-box',pointerEvents:'none'}}));
  // maic guide: cyan line is the page boundary kept by maic; the green band
  // between it and the content guide is the configured preserved margin.
  const _maicCrop=cropData&&cropData.maic_preview_crop;
  const _maicContent=cropData&&cropData.maic_content_crop;
  // A manual crop supersedes maic crop for this page immediately.  The
  // current cropData still contains the previous automatic guides until the
  // preview is requested again, so do not keep drawing their cyan boundary
  // or preserved-margin mask while the user is editing a custom frame.
  if(!isCustom&&cropData&&cropData.maic_crop_applied&&_maicCrop){
    const mt=_ry((_maicCrop.top/natH*100).toFixed(3));
    const mb=_ry(((natH-1-_maicCrop.bottom)/natH*100).toFixed(3));
    const ml=_rx((_maicCrop.left/natW*100).toFixed(3));
    const mr=_rx(((natW-1-_maicCrop.right)/natW*100).toFixed(3));
    const mtEnd=100-mb,mrEnd=100-mr;
    if(_maicContent){
      const ct=_ry((_maicContent.top/natH*100).toFixed(3));
      const cb=_ry(((natH-1-_maicContent.bottom)/natH*100).toFixed(3));
      const cl=_rx((_maicContent.left/natW*100).toFixed(3));
      const cr=_rx(((natW-1-_maicContent.right)/natW*100).toFixed(3));
      const cbEnd=100-cb,crEnd=100-cr;
      const saved='rgba(34,197,94,0.20)';
      if(ct>mt)wrap.append(h('div',{style:{position:'absolute',top:mt+'%',left:ml+'%',width:(mrEnd-ml)+'%',height:(ct-mt)+'%',background:saved}}));
      if(mtEnd>cbEnd)wrap.append(h('div',{style:{position:'absolute',top:cbEnd+'%',left:ml+'%',width:(mrEnd-ml)+'%',height:(mtEnd-cbEnd)+'%',background:saved}}));
      if(cl>ml)wrap.append(h('div',{style:{position:'absolute',top:ct+'%',left:ml+'%',width:(cl-ml)+'%',height:(cbEnd-ct)+'%',background:saved}}));
      if(mrEnd>crEnd)wrap.append(h('div',{style:{position:'absolute',top:ct+'%',left:crEnd+'%',width:(mrEnd-crEnd)+'%',height:(cbEnd-ct)+'%',background:saved}}));
      wrap.append(h('div',{style:{position:'absolute',top:ct+'%',left:cl+'%',width:(crEnd-cl)+'%',height:(cbEnd-ct)+'%',
        border:'1px dotted rgba(34,197,94,0.72)',boxSizing:'border-box',pointerEvents:'none'}}));
    }
    wrap.append(h('div',{style:{position:'absolute',top:mt+'%',left:ml+'%',width:(mrEnd-ml)+'%',height:(mtEnd-mt)+'%',
      border:'1.5px dashed rgba(34,211,238,0.92)',boxSizing:'border-box',pointerEvents:'none'}}));
    const pct=Number(cropData.maic_margin_pct||0).toFixed(1);
    const px=parseInt(cropData.maic_margin_px,10)||0;
    wrap.append(h('div',{style:{position:'absolute',top:'calc('+mt+'% + 4px)',left:'calc('+ml+'% + 4px)',
      background:'rgba(8,47,73,0.88)',border:'1px solid rgba(34,211,238,0.55)',borderRadius:'999px',
      color:'#cffafe',fontSize:'0.54rem',fontWeight:'700',padding:'2px 6px',pointerEvents:'none',zIndex:'12'}},
      `maic ${pct}% · ${px}px`));
  }
  // Margin fill strips between mask and crop boundary
  if(_emT||_emB||_emL||_emR){
    const fillColor=_getExtraMarginFillColor(relPath);
    const gc='rgba(34,197,94,0.6)';
    if(_emT&&cropT>mTy){
      wrap.append(h('div',{style:{position:'absolute',top:mTy+'%',left:mLx+'%',width:(mRx-mLx)+'%',
        height:(cropT-mTy)+'%',
        background:fillColor,borderBottom:'1.5px dashed '+gc,boxSizing:'border-box'}}));
    }
    if(_emB&&mBy>cropB){
      wrap.append(h('div',{style:{position:'absolute',top:cropB+'%',left:mLx+'%',width:(mRx-mLx)+'%',
        height:(mBy-cropB)+'%',
        background:fillColor,borderTop:'1.5px dashed '+gc,boxSizing:'border-box'}}));
    }
    if(_emL&&cropL>mLx){
      wrap.append(h('div',{style:{position:'absolute',top:cropT+'%',left:mLx+'%',width:(cropL-mLx)+'%',
        height:(cropB-cropT)+'%',
        background:fillColor,borderRight:'1.5px dashed '+gc,boxSizing:'border-box'}}));
    }
    if(_emR&&mRx>cropR){
      wrap.append(h('div',{style:{position:'absolute',top:cropT+'%',left:cropR+'%',width:(mRx-cropR)+'%',
        height:(cropB-cropT)+'%',
        background:fillColor,borderLeft:'1.5px dashed '+gc,boxSizing:'border-box'}}));
    }
  }
  // Wrap-relative crop positions for handles and inter-panel
  const _cropTw=cropT,_cropBw=100-cropB,_cropLw=cropL,_cropRw=100-cropR;
  if(!isCustom&&(interRows.length||interCols.length)){
    const innerBg='rgba(251,191,36,0.20)';
    const innerBd='rgba(251,191,36,0.40)';
    interRows.forEach(pair=>{
      if(!Array.isArray(pair)||pair.length<2)return;
      const y0=Math.max(0,Math.min(natH-1,parseInt(pair[0],10)));
      const y1=Math.max(0,Math.min(natH-1,parseInt(pair[1],10)));
      if(y1<y0)return;
      const top=_ry(((y0/natH)*100).toFixed(3));
      const hh=_rh(((((y1-y0+1)/natH)*100)).toFixed(3));
      wrap.append(h('div',{style:{position:'absolute',top:top+'%',left:cropL+'%',width:(cropR-cropL)+'%',height:hh+'%',
        background:innerBg,borderTop:'1px solid '+innerBd,borderBottom:'1px solid '+innerBd,boxSizing:'border-box'}}));
    });
    interCols.forEach(pair=>{
      if(!Array.isArray(pair)||pair.length<2)return;
      const x0=Math.max(0,Math.min(natW-1,parseInt(pair[0],10)));
      const x1=Math.max(0,Math.min(natW-1,parseInt(pair[1],10)));
      if(x1<x0)return;
      const left=_rx(((x0/natW)*100).toFixed(3));
      const ww=_rw(((((x1-x0+1)/natW)*100)).toFixed(3));
      wrap.append(h('div',{style:{position:'absolute',top:cropT+'%',height:(cropB-cropT)+'%',left:left+'%',width:ww+'%',
        background:innerBg,borderLeft:'1px solid '+innerBd,borderRight:'1px solid '+innerBd,boxSizing:'border-box'}}));
    });
  }

  if(isCustom&&relPath){
    const badge=h('div',{style:{position:'absolute',top:'4px',right:'4px',background:'rgba(100,150,255,0.85)',
      color:'#fff',fontSize:'0.55rem',fontWeight:'600',padding:'2px 6px',borderRadius:'4px',pointerEvents:'auto',cursor:'pointer',
      display:'flex',alignItems:'center',gap:'3px'},
      title:t('conv.crop_reset','Reset to auto'),
      onClick:()=>{delete S.convCustomCrop[relPath];_invalidateCropCaches();render();}});
    badge.textContent='\u2702 '+t('conv.crop_custom','Custom');
    wrap.append(badge);
  }
  const hs='6px';
  const _saveCrop=()=>{
    if(!canEdit||!relPath)return;
    const e2=S._editCrop;
    if(e2.top!==origCrop.top||e2.bottom!==origCrop.bottom||e2.left!==origCrop.left||e2.right!==origCrop.right){
      S.convCustomCrop[relPath]={top:e2.top,bottom:e2.bottom,left:e2.left,right:e2.right,width:natW,height:natH};
    } else {
      delete S.convCustomCrop[relPath];
    }
  };
  const mkHandle=(cursor,posStyle,onDrag)=>{
    const handle=h('div',{style:{position:'absolute',pointerEvents:'auto',zIndex:'16',cursor,...posStyle,background:'transparent'}});
    handle.addEventListener('mousedown',e=>{
      e.preventDefault();e.stopPropagation();
      const startX=e.clientX,startY=e.clientY;
      const startCrop={...S._editCrop};
      const imgRect=imgEl.getBoundingClientRect();
      const onMove=ev=>{
        const dx=ev.clientX-startX,dy=ev.clientY-startY;
        const scale=S.convViewScale||1;
        onDrag(dx/scale,dy/scale,startCrop,natW,natH,imgRect.width/natW/scale,imgRect.height/natH/scale);
        while(wrap.firstChild)wrap.removeChild(wrap.firstChild);
        _drawCropOverlay(container,imgEl,cropData,relPath);
      };
      const onUp=()=>{
        document.removeEventListener('mousemove',onMove);
        document.removeEventListener('mouseup',onUp);
        _saveCrop();
      };
      document.addEventListener('mousemove',onMove);
      document.addEventListener('mouseup',onUp);
    });
    wrap.append(handle);
  };

  if(canEdit){
    mkHandle('ns-resize',{left:cropL+'%',width:(cropR-cropL)+'%',top:'calc('+cropT+'% - '+hs+')',height:'calc('+hs+' * 2)'},
      (dx,dy,sc,nw,nh,sx,sy)=>{S._editCrop.top=Math.max(0,Math.min(Math.round(nh*0.45),Math.round(sc.top+dy/sy)));});
    mkHandle('ns-resize',{left:cropL+'%',width:(cropR-cropL)+'%',bottom:'calc('+_cropBw+'% - '+hs+')',height:'calc('+hs+' * 2)'},
      (dx,dy,sc,nw,nh,sx,sy)=>{S._editCrop.bottom=Math.max(Math.round(nh*0.55),Math.min(nh-1,Math.round(sc.bottom+dy/sy)));});
    mkHandle('ew-resize',{top:cropT+'%',height:(cropB-cropT)+'%',left:'calc('+cropL+'% - '+hs+')',width:'calc('+hs+' * 2)'},
      (dx,dy,sc,nw,nh,sx,sy)=>{S._editCrop.left=Math.max(0,Math.min(Math.round(nw*0.45),Math.round(sc.left+dx/sx)));});
    mkHandle('ew-resize',{top:cropT+'%',height:(cropB-cropT)+'%',right:'calc('+_cropRw+'% - '+hs+')',width:'calc('+hs+' * 2)'},
      (dx,dy,sc,nw,nh,sx,sy)=>{S._editCrop.right=Math.max(Math.round(nw*0.55),Math.min(nw-1,Math.round(sc.right+dx/sx)));});
  }

  container.append(wrap);
}
function _convGetSplitRegionsForVariant(natW,natH,mangaMode){
  if(natW>natH){
    const mid=Math.floor(natW/2);
    const left={x0:0,y0:0,w:Math.max(1,mid),h:natH};
    left.x1=left.x0+left.w-1;left.y1=left.y0+left.h-1;
    const right={x0:mid,y0:0,w:Math.max(1,natW-mid),h:natH};
    right.x1=right.x0+right.w-1;right.y1=right.y0+right.h-1;
    return {S1:mangaMode?right:left,S2:mangaMode?left:right};
  }
  if(natH>natW){
    const mid=Math.floor(natH/2);
    const top={x0:0,y0:0,w:natW,h:Math.max(1,mid)};
    top.x1=top.x0+top.w-1;top.y1=top.y0+top.h-1;
    const bottom={x0:0,y0:mid,w:natW,h:Math.max(1,natH-mid)};
    bottom.x1=bottom.x0+bottom.w-1;bottom.y1=bottom.y0+bottom.h-1;
    return {S1:mangaMode?bottom:top,S2:mangaMode?top:bottom};
  }
  return null;
}
function _convClampCropToImage(natW,natH,crop){
  const c=crop||{};
  const left=Math.max(0,Math.min(natW-1,parseInt(c.left,10)));
  const right=Math.max(left,Math.min(natW-1,parseInt(c.right,10)));
  const top=Math.max(0,Math.min(natH-1,parseInt(c.top,10)));
  const bottom=Math.max(top,Math.min(natH-1,parseInt(c.bottom,10)));
  return {
    left:Number.isFinite(left)?left:0,
    right:Number.isFinite(right)?right:(natW-1),
    top:Number.isFinite(top)?top:0,
    bottom:Number.isFinite(bottom)?bottom:(natH-1)
  };
}
// Which way the bisecting cut runs. A page only counts as a spread when it lies
// the other way round from the device, so the device alone settles it: on an
// upright Kindle a spread is always a wide page and is always cut down the
// middle, never across. Measuring the page instead read the paper rather than
// the cut -- a portrait page whose blank top and bottom the crop takes away is
// landscape by the time it is bisected, and that trimming is the whole reason it
// counts as a spread, yet the untrimmed page said "cut across" and the preview
// laid the two bands side by side.
function _convSplitAxisForDevice(){
  const pinfo=_getActiveConvProfileInfo();
  const pw=pinfo&&Number.isFinite(Number(pinfo.width))?parseInt(pinfo.width,10):0;
  const ph=pinfo&&Number.isFinite(Number(pinfo.height))?parseInt(pinfo.height,10):0;
  if(!(pw>0&&ph>0))return null;
  return pw>ph?'y':'x';
}
function _convGetSplitRegionsForCrop(natW,natH,crop){
  if(!(natW>0&&natH>0))return null;
  const ec=_convClampCropToImage(natW,natH,crop);
  const cropW=Math.max(1,(ec.right-ec.left+1));
  const cropH=Math.max(1,(ec.bottom-ec.top+1));
  // Without a device to ask, fall back on the shape the cut is made from -- the
  // cropped page, not the paper around it.
  const axis=_convSplitAxisForDevice()||(cropW>=cropH?'x':'y');
  if(axis==='x'){
    const split=ec.left+Math.floor(cropW/2);
    const leftW=Math.max(1,split-ec.left);
    const rightW=Math.max(1,ec.right-split+1);
    const left={x0:ec.left,y0:ec.top,w:leftW,h:Math.max(1,ec.bottom-ec.top+1)};
    left.x1=left.x0+left.w-1;left.y1=left.y0+left.h-1;
    const right={x0:split,y0:ec.top,w:rightW,h:Math.max(1,ec.bottom-ec.top+1)};
    right.x1=right.x0+right.w-1;right.y1=right.y0+right.h-1;
    return {axis:'x',split,left,right,crop:ec,total:natW};
  }
  const split=ec.top+Math.floor(cropH/2);
  const topH=Math.max(1,split-ec.top);
  const bottomH=Math.max(1,ec.bottom-split+1);
  const top={x0:ec.left,y0:ec.top,w:Math.max(1,ec.right-ec.left+1),h:topH};
  top.x1=top.x0+top.w-1;top.y1=top.y0+top.h-1;
  const bottom={x0:ec.left,y0:split,w:Math.max(1,ec.right-ec.left+1),h:bottomH};
  bottom.x1=bottom.x0+bottom.w-1;bottom.y1=bottom.y0+bottom.h-1;
  return {axis:'y',split,top,bottom,crop:ec,total:natH};
}
function _convBuildSplitRegionsByAxis(natW,natH,axis,rawSplit){
  if(!(natW>0&&natH>0))return null;
  const ax=String(axis||'').toLowerCase()==='y'?'y':'x';
  if(ax==='x'){
    if(natW<2)return null;
    const split=Math.max(1,Math.min(natW-1,parseInt(rawSplit,10)||Math.floor(natW/2)));
    const left={x0:0,y0:0,w:Math.max(1,split),h:natH};
    left.x1=left.x0+left.w-1;left.y1=left.y0+left.h-1;
    const right={x0:split,y0:0,w:Math.max(1,natW-split),h:natH};
    right.x1=right.x0+right.w-1;right.y1=right.y0+right.h-1;
    return {axis:'x',split,left,right,crop:{left:0,right:natW-1,top:0,bottom:natH-1},total:natW};
  }
  if(natH<2)return null;
  const split=Math.max(1,Math.min(natH-1,parseInt(rawSplit,10)||Math.floor(natH/2)));
  const top={x0:0,y0:0,w:natW,h:Math.max(1,split)};
  top.x1=top.x0+top.w-1;top.y1=top.y0+top.h-1;
  const bottom={x0:0,y0:split,w:natW,h:Math.max(1,natH-split)};
  bottom.x1=bottom.x0+bottom.w-1;bottom.y1=bottom.y0+bottom.h-1;
  return {axis:'y',split,top,bottom,crop:{left:0,right:natW-1,top:0,bottom:natH-1},total:natH};
}
function _convGetCustomSplitForImage(relPath,natW,natH){
  const rp=_convNormPath(relPath);
  if(!rp||!(natW>1&&natH>1))return null;
  const raw=S.convCustomSplit&&S.convCustomSplit[rp];
  if(!raw||typeof raw!=='object')return null;
  const axisRaw=String(raw.axis||'').toLowerCase();
  const axis=(axisRaw==='x'||axisRaw==='y')?axisRaw:(_convSplitAxisForDevice()||(natW>=natH?'x':'y'));
  const total=axis==='x'?natW:natH;
  const srcTotal=axis==='x'?(parseInt(raw.width,10)||0):(parseInt(raw.height,10)||0);
  let split=parseFloat(raw.split);
  if(!Number.isFinite(split))split=Math.floor(total/2);
  if(srcTotal>0&&srcTotal!==total){
    split=(split/srcTotal)*total;
  }
  split=Math.max(1,Math.min(total-1,Math.round(split)));
  return {axis,split,width:natW,height:natH};
}
function _convSetCustomSplitForImage(relPath,natW,natH,split,axis){
  const rp=_convNormPath(relPath);
  if(!rp||!(natW>1&&natH>1))return;
  const ax=String(axis||'').toLowerCase()==='y'?'y':'x';
  const total=ax==='x'?natW:natH;
  const clamped=Math.max(1,Math.min(total-1,Math.round(parseFloat(split)||Math.floor(total/2))));
  S.convCustomSplit[rp]={axis:ax,split:clamped,width:natW,height:natH};
}
function _convGetPreviewSplitRegionsForCrop(natW,natH,crop){
  if(!(natW>0&&natH>0))return null;
  const regs=_convGetSplitRegionsForCrop(natW,natH,crop);
  if(!regs)return null;
  if(regs.axis==='x'){
    if(natW<2)return regs;
    const split=Math.max(1,Math.min(natW-1,parseInt(regs.split,10)||Math.floor(natW/2)));
    const left={x0:0,y0:0,w:Math.max(1,split),h:natH};
    left.x1=left.x0+left.w-1;left.y1=left.y0+left.h-1;
    const right={x0:split,y0:0,w:Math.max(1,natW-split),h:natH};
    right.x1=right.x0+right.w-1;right.y1=right.y0+right.h-1;
    return {axis:'x',split,left,right,crop:regs.crop,total:natW};
  }
  if(natH<2)return regs;
  const split=Math.max(1,Math.min(natH-1,parseInt(regs.split,10)||Math.floor(natH/2)));
  const top={x0:0,y0:0,w:natW,h:Math.max(1,split)};
  top.x1=top.x0+top.w-1;top.y1=top.y0+top.h-1;
  const bottom={x0:0,y0:split,w:natW,h:Math.max(1,natH-split)};
  bottom.x1=bottom.x0+bottom.w-1;bottom.y1=bottom.y0+bottom.h-1;
  return {axis:'y',split,top,bottom,crop:regs.crop,total:natH};
}
function _convGetRegionByVariantForCrop(variant,splitRegs,mangaMode){
  if(!splitRegs)return null;
  const v=String(variant||'').toUpperCase();
  if(splitRegs.axis==='x'){
    const leftVariant='S2';
    return v===leftVariant?splitRegs.left:splitRegs.right;
  }
  const topVariant='S2';
  return v===topVariant?splitRegs.top:splitRegs.bottom;
}
function _drawCropOverlayPairSplit(slots,cropData,relPath){
  if(!Array.isArray(slots)||slots.length<1||!cropData||!cropData.crop)return false;
  const natW=Math.max(1,parseInt(cropData.width,10)||0);
  const natH=Math.max(1,parseInt(cropData.height,10)||0);
  // Which slot owns which editable edge has to hold still while an edge is
  // dragged, so it is read off the crop the preview came back with rather than
  // the live one -- but off a crop all the same, so it runs the same way as the
  // cut the slots are showing.
  const _fixedCrop=(cropData&&cropData.crop)||{left:0,right:natW-1,top:0,bottom:natH-1};
  const _basePreviewRegs=_convGetPreviewSplitRegionsForCrop(natW,natH,_fixedCrop);
  const previewVariant=String((cropData&&cropData.preview_variant)||'N').toUpperCase();
  const canEdit=!!relPath&&previewVariant==='N';
  const cropKey=natW+'x'+natH+'|'+(relPath||'')+'|'+previewVariant;
  if(!S._editCrop||S._editCropKey!==cropKey){
    const custom=canEdit&&relPath?S.convCustomCrop[relPath]:null;
    if(canEdit&&custom&&custom.width===natW&&custom.height===natH){
      S._editCrop={top:custom.top,bottom:custom.bottom,left:custom.left,right:custom.right};
    } else {
      S._editCrop={...cropData.crop};
    }
    S._editCropKey=cropKey;
  }
  const origCrop=cropData.crop;
  const inter=(cropData&&cropData.inter_panel)||{};
  const interRows=Array.isArray(inter.rows)?inter.rows:[];
  const interCols=Array.isArray(inter.cols)?inter.cols:[];
  const hs='6px';
  const _saveCrop=()=>{
    if(!canEdit||!relPath)return;
    const e2=S._editCrop;
    if(e2.top!==origCrop.top||e2.bottom!==origCrop.bottom||e2.left!==origCrop.left||e2.right!==origCrop.right){
      S.convCustomCrop[relPath]={top:e2.top,bottom:e2.bottom,left:e2.left,right:e2.right,width:natW,height:natH};
    } else {
      delete S.convCustomCrop[relPath];
    }
  };
  const _slotInfos=slots.map((slot,idx)=>{
    const variant=String(slot&&slot.variant||'').toUpperCase();
    const renderVariant=String(slot&&slot.renderVariant||variant).toUpperCase();
    const region=_convGetRegionByVariantForCrop(renderVariant,_basePreviewRegs,!!S.convManga);
    return {...slot,variant,renderVariant,baseRegion:region||null,idx};
  }).filter(Boolean);
  if(_slotInfos.length<1)return false;
  const _fixedRegs=_basePreviewRegs;
  const _localCrop=(reg,c)=>{
    const gy0=Math.max(c.top,reg.y0),gy1=Math.min(c.bottom,reg.y1);
    const gx0=Math.max(c.left,reg.x0),gx1=Math.min(c.right,reg.x1);
    const ly0=Math.max(0,Math.min(reg.h-1,gy0-reg.y0));
    const ly1=Math.max(ly0,Math.min(reg.h-1,gy1-reg.y0));
    const lx0=Math.max(0,Math.min(reg.w-1,gx0-reg.x0));
    const lx1=Math.max(lx0,Math.min(reg.w-1,gx1-reg.x0));
    return {top:ly0,bottom:ly1,left:lx0,right:lx1};
  };
  const _fixedRegionForSlot=(si)=>{
    if(_fixedRegs){
      const mapped=_convGetRegionByVariantForCrop(si.renderVariant||si.variant,_fixedRegs,!!S.convManga);
      if(mapped)return mapped;
    }
    return si.baseRegion;
  };
  const _regionForSlot=(si,regs)=>{
    const mapped=_convGetRegionByVariantForCrop(si.renderVariant||si.variant,regs,!!S.convManga);
    if(mapped)return mapped;
    return _fixedRegionForSlot(si);
  };
  const _redraw=()=>{
    const ec=S._editCrop;
    const splitRegs=_convGetSplitRegionsForCrop(natW,natH,ec);
    const previewRegs=_convGetPreviewSplitRegionsForCrop(natW,natH,ec);
    if(typeof _slotInfos[0].onEditCrop==='function'){
      try{_slotInfos[0].onEditCrop(ec,splitRegs,{natW,natH});}catch(_e){}
    }
    const isCustom=canEdit&&(ec.top!==origCrop.top||ec.bottom!==origCrop.bottom||ec.left!==origCrop.left||ec.right!==origCrop.right);
    const mc=isCustom?'rgba(100,150,255,0.22)':'rgba(255,50,50,0.22)';
    const bc=isCustom?'rgba(100,150,255,0.6)':'rgba(255,120,80,0.6)';
    _slotInfos.forEach((si,idx)=>{
      const container=si.wrap;
      if(!container)return;
      const old=container.querySelector('.crop-overlay-wrap');
      if(old)old.remove();
      const region=_regionForSlot(si,previewRegs);
      if(!region)return;
      const lc=_localCrop(region,ec);
      const tPct=(lc.top/region.h*100).toFixed(3);
      const bPct=((region.h-1-lc.bottom)/region.h*100).toFixed(3);
      const lPct=(lc.left/region.w*100).toFixed(3);
      const rPct=((region.w-1-lc.right)/region.w*100).toFixed(3);
      const wrap=h('div',{className:'crop-overlay-wrap',style:{position:'absolute',top:'0',left:'0',width:'100%',height:'100%',pointerEvents:'none'}});
      wrap.append(h('div',{style:{position:'absolute',top:'0',left:'0',width:'100%',height:tPct+'%',background:mc}}));
      wrap.append(h('div',{style:{position:'absolute',bottom:'0',left:'0',width:'100%',height:bPct+'%',background:mc}}));
      wrap.append(h('div',{style:{position:'absolute',top:tPct+'%',left:'0',width:lPct+'%',height:(100-parseFloat(tPct)-parseFloat(bPct))+'%',background:mc}}));
      wrap.append(h('div',{style:{position:'absolute',top:tPct+'%',right:'0',width:rPct+'%',height:(100-parseFloat(tPct)-parseFloat(bPct))+'%',background:mc}}));
      wrap.append(h('div',{style:{position:'absolute',top:tPct+'%',left:lPct+'%',right:rPct+'%',bottom:bPct+'%',
        border:'1.5px dashed '+bc,boxSizing:'border-box',pointerEvents:'none'}}));
      const maicGlobal=cropData&&cropData.maic_preview_crop;
      const contentGlobal=cropData&&cropData.maic_content_crop;
      if(!isCustom&&cropData&&cropData.maic_crop_applied&&maicGlobal){
        const mcrop=_localCrop(region,maicGlobal);
        const mt=mcrop.top/region.h*100,mb=(region.h-1-mcrop.bottom)/region.h*100;
        const ml=mcrop.left/region.w*100,mr=(region.w-1-mcrop.right)/region.w*100;
        const mBottom=100-mb,mRight=100-mr;
        if(contentGlobal){
          const ccrop=_localCrop(region,contentGlobal);
          const ct=ccrop.top/region.h*100,cb=(region.h-1-ccrop.bottom)/region.h*100;
          const cl=ccrop.left/region.w*100,cr=(region.w-1-ccrop.right)/region.w*100;
          const cBottom=100-cb,cRight=100-cr;
          const saved='rgba(34,197,94,0.20)';
          if(ct>mt)wrap.append(h('div',{style:{position:'absolute',top:mt+'%',left:ml+'%',width:(mRight-ml)+'%',height:(ct-mt)+'%',background:saved}}));
          if(mBottom>cBottom)wrap.append(h('div',{style:{position:'absolute',top:cBottom+'%',left:ml+'%',width:(mRight-ml)+'%',height:(mBottom-cBottom)+'%',background:saved}}));
          if(cl>ml)wrap.append(h('div',{style:{position:'absolute',top:ct+'%',left:ml+'%',width:(cl-ml)+'%',height:(cBottom-ct)+'%',background:saved}}));
          if(mRight>cRight)wrap.append(h('div',{style:{position:'absolute',top:ct+'%',left:cRight+'%',width:(mRight-cRight)+'%',height:(cBottom-ct)+'%',background:saved}}));
        }
        wrap.append(h('div',{style:{position:'absolute',top:mt+'%',left:ml+'%',width:(mRight-ml)+'%',height:(mBottom-mt)+'%',
          border:'1.5px dashed rgba(34,211,238,0.92)',boxSizing:'border-box',pointerEvents:'none'}}));
        if(idx===0){
          const pct=Number(cropData.maic_margin_pct||0).toFixed(1),px=parseInt(cropData.maic_margin_px,10)||0;
          wrap.append(h('div',{style:{position:'absolute',top:'calc('+mt+'% + 4px)',left:'calc('+ml+'% + 4px)',
            background:'rgba(8,47,73,0.88)',border:'1px solid rgba(34,211,238,0.55)',borderRadius:'999px',
            color:'#cffafe',fontSize:'0.54rem',fontWeight:'700',padding:'2px 6px',pointerEvents:'none',zIndex:'12'}},
            `maic ${pct}% · ${px}px`));
        }
      }
      if(!isCustom&&(interRows.length||interCols.length)){
        const innerBg='rgba(251,191,36,0.20)';
        const innerBd='rgba(251,191,36,0.40)';
        interRows.forEach(pair=>{
          if(!Array.isArray(pair)||pair.length<2)return;
          const y0=Math.max(0,Math.min(natH-1,parseInt(pair[0],10)));
          const y1=Math.max(0,Math.min(natH-1,parseInt(pair[1],10)));
          if(y1<y0)return;
          const top=((y0-region.y0)/region.h*100).toFixed(3);
          const hh=(((y1-y0+1)/region.h)*100).toFixed(3);
          wrap.append(h('div',{style:{position:'absolute',top:top+'%',left:lPct+'%',right:rPct+'%',height:hh+'%',
            background:innerBg,borderTop:'1px solid '+innerBd,borderBottom:'1px solid '+innerBd,boxSizing:'border-box'}}));
        });
        interCols.forEach(pair=>{
          if(!Array.isArray(pair)||pair.length<2)return;
          const x0=Math.max(0,Math.min(natW-1,parseInt(pair[0],10)));
          const x1=Math.max(0,Math.min(natW-1,parseInt(pair[1],10)));
          const ix0=Math.max(x0,region.x0),ix1=Math.min(x1,region.x1);
          if(ix1<ix0)return;
          const left=((ix0-region.x0)/region.w*100).toFixed(3);
          const ww=(((ix1-ix0+1)/region.w)*100).toFixed(3);
          wrap.append(h('div',{style:{position:'absolute',top:tPct+'%',bottom:bPct+'%',left:left+'%',width:ww+'%',
            background:innerBg,borderLeft:'1px solid '+innerBd,borderRight:'1px solid '+innerBd,boxSizing:'border-box'}}));
        });
      }
      let _isLeftHalf=si.side==='left',_isRightHalf=si.side==='right';
      if(!_isLeftHalf&&!_isRightHalf&&_fixedRegs&&_fixedRegs.axis==='x'){
        // Determine editable edge by stable slot variant, not by shifted preview region.
        const fixedByVariant=_convGetRegionByVariantForCrop(si.renderVariant||si.variant,_fixedRegs,!!S.convManga);
        if(fixedByVariant){
          _isLeftHalf=fixedByVariant.x0===_fixedRegs.left.x0&&fixedByVariant.x1===_fixedRegs.left.x1;
          _isRightHalf=fixedByVariant.x0===_fixedRegs.right.x0&&fixedByVariant.x1===_fixedRegs.right.x1;
        } else {
          _isLeftHalf=region.x0===_fixedRegs.left.x0&&region.x1===_fixedRegs.left.x1;
          _isRightHalf=region.x0===_fixedRegs.right.x0&&region.x1===_fixedRegs.right.x1;
        }
      } else if(!_isLeftHalf&&!_isRightHalf) {
        _isLeftHalf=region.x0===0;
        _isRightHalf=region.x1===natW-1;
      }
      if(isCustom&&relPath&&_isRightHalf){
        const badge=h('div',{style:{position:'absolute',top:'4px',right:'4px',background:'rgba(100,150,255,0.85)',
          color:'#fff',fontSize:'0.55rem',fontWeight:'600',padding:'2px 6px',borderRadius:'4px',pointerEvents:'auto',cursor:'pointer',
          display:'flex',alignItems:'center',gap:'3px'},
          title:t('conv.crop_reset','Reset to auto'),
          onClick:()=>{delete S.convCustomCrop[relPath];_invalidateCropCaches();render();}});
        badge.textContent='\u2702 '+t('conv.crop_custom','Custom');
        wrap.append(badge);
      }
      const mkHandle=(cursor,posStyle,onDrag)=>{
        const handle=h('div',{style:{position:'absolute',pointerEvents:'auto',zIndex:'16',cursor,...posStyle,background:'transparent'}});
        handle.addEventListener('mousedown',e=>{
          e.preventDefault();e.stopPropagation();
          const startX=e.clientX,startY=e.clientY;
          const startCrop={...S._editCrop};
          const imgRect=si.img.getBoundingClientRect();
          const scale=S.convViewScale||1;
          const sx=imgRect.width/Math.max(1,region.w)/scale;
          const sy=imgRect.height/Math.max(1,region.h)/scale;
          const onMove=ev=>{
            const dx=ev.clientX-startX,dy=ev.clientY-startY;
            onDrag(dx,dy,startCrop,sx,sy);
            _redraw();
            if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
          };
          const onUp=()=>{
            document.removeEventListener('mousemove',onMove);
            document.removeEventListener('mouseup',onUp);
            _saveCrop();
            _redraw();
            if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
          };
          document.addEventListener('mousemove',onMove);
          document.addEventListener('mouseup',onUp);
        });
        wrap.append(handle);
      };
      if(canEdit){
        mkHandle('ns-resize',{left:'0',right:'0',top:'calc('+tPct+'% - '+hs+')',height:'calc('+hs+' * 2)'},
          (dx,dy,sc,sx,sy)=>{S._editCrop.top=Math.max(0,Math.min(Math.round(natH*0.45),Math.round(sc.top+dy/sy)));});
        mkHandle('ns-resize',{left:'0',right:'0',bottom:'calc('+bPct+'% - '+hs+')',height:'calc('+hs+' * 2)'},
          (dx,dy,sc,sx,sy)=>{S._editCrop.bottom=Math.max(Math.round(natH*0.55),Math.min(natH-1,Math.round(sc.bottom+dy/sy)));});
        if(_isLeftHalf){
          mkHandle('ew-resize',{top:tPct+'%',bottom:bPct+'%',left:'calc('+lPct+'% - '+hs+')',width:'calc('+hs+' * 2)'},
            (dx,dy,sc,sx,sy)=>{S._editCrop.left=Math.max(0,Math.min(Math.round(natW*0.45),Math.round(sc.left+dx/sx)));});
        }
        if(_isRightHalf){
          mkHandle('ew-resize',{top:tPct+'%',bottom:bPct+'%',right:'calc('+rPct+'% - '+hs+')',width:'calc('+hs+' * 2)'},
            (dx,dy,sc,sx,sy)=>{S._editCrop.right=Math.max(Math.round(natW*0.55),Math.min(natW-1,Math.round(sc.right+dx/sx)));});
        }
      }
      container.append(wrap);
      _drawPageNumberRemovalMasks(container,cropData,region);
    });
  };
  _redraw();
  return true;
}
function clearMask(){
  if(!maskCtx)return;
  _startEditing();
  _pushUndo();
  maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);
  drawOverlay();
  const f=curFile();
  if(f){
    delete S.detections[f.path];
    S.status='Enter \u2014 apply, Esc \u2014 cancel';
    apiPost('/api/batch/remove-detection',{path:f.path}).catch(()=>{});
    // Save empty mask as temp so render preserves it
    const d=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);
    f._maskData=new Uint8ClampedArray(d.data);
  }
  render();setTimeout(loadCurrentImage,30);
}

function navImage(dir){
  S.artifactCapture=null;S.artifactDraft=null;
  if(_maskEditing){
    cancelMaskEdit();
  }
  saveMask();resetView();S.cleanViewOpen=true;S.idx+=dir;
  if(S.idx<0)S.idx=S.allFiles.length-1;if(S.idx>=S.allFiles.length)S.idx=0;
  const nf=curFile();if(nf){if(!S._thumbEpoch)S._thumbEpoch={};S._thumbEpoch[nf.path]=Date.now();}
  render();setTimeout(loadCurrentImage,30);
}

// Encoding-normalized comment.
async function detectCurrent(){
  const f=curFile();if(!f)return;
  S.processing=true;S.status=t('clean.detecting');render();
  try{
    const r=await(await apiPost('/api/detect-path',{path:f.path,confidence:S.confidence})).json();
    if(r.boxes&&r.boxes.length>0){
      S.detections[f.path]={boxes:r.boxes, masks:r.masks||[]};
      S.status=`${r.boxes.length} ${t('clean.artifacts_word','artifacts')}`;
      // Clear saved mask so loadCurrentImage will auto-draw
      f._maskData=null;
    }else{S.status=r.error||t('clean.nothing_found');}
  }catch(e){S.status=t('clean.error','Error: ')+e.message;}
  S.processing=false;render();setTimeout(loadCurrentImage,30);
}

// Encoding-normalized comment.
async function cleanCurrent(){
  const f=curFile();if(!f||!maskCanvas)return;
  S.processing=true;S.status=t('clean.cleaning');render();
  try{
    const tc=document.createElement('canvas');tc.width=maskCanvas.width;tc.height=maskCanvas.height;
    const tctx=tc.getContext('2d');const md=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);
    const out=tctx.createImageData(maskCanvas.width,maskCanvas.height);
    let hasMask=false;
    for(let i=0;i<maskCanvas.width*maskCanvas.height;i++){const v=md.data[i*4+3]>0?255:0;if(v)hasMask=true;out.data[i*4]=v;out.data[i*4+1]=v;out.data[i*4+2]=v;out.data[i*4+3]=255;}
    if(!hasMask){S.status=t('clean.mask_empty');S.processing=false;render();return;}
    tctx.putImageData(out,0,0);
    const maskBlob=await new Promise(r=>tc.toBlob(r,'image/png'));
    const fd=new FormData();
    fd.append('path',f.path);
    fd.append('mask',maskBlob,'mask.png');
    fd.append('method',S.cleanMethod);
    fd.append('padding',String(S.maskPadding));
    fd.append('output_dir',S.outputDir);
    fd.append('root_dir',S.rootFolder);
    fd.append('has_subfolders',S.hasSubfolders?'true':'false');
    const r=await apiPost('/api/clean-path',fd);
    const blob=await r.blob();
    S.cleanedPaths[f.path]=Date.now();
    f._cleanedUrl=URL.createObjectURL(blob);
    S.status='\u2713 '+t('clean.saved_to','Saved to ')+S.outputDir;
  }catch(e){S.status=t('clean.error','Error: ')+e.message;}
  S.processing=false;render();
}

// Encoding-normalized comment.
async function batchDetect(){
  if(S.allFiles.length===0)return;
  const files=S.allFiles.map(f=>({path:f.path,name:f.name,folder:f.folder}));
  try{
    const r=await(await apiPost('/api/batch/detect',{files,confidence:S.confidence})).json();
    if(!r.ok){alert(r.error);return;}
    S.progressOwner='batch';S.batchPollId=setInterval(pollBatch,500);
    S.batch.running=true;S.batch.phase='detect';render();
  }catch(e){alert(e.message);}
}

// Encoding-normalized comment.
async function batchClean(){
  if(!S.outputDir){alert(t('clean.no_export_dir'));return;}
  try{
    const r=await(await apiPost('/api/batch/clean',{
      method:S.cleanMethod, padding:S.maskPadding,
      output_dir:S.outputDir, root_dir:S.rootFolder,
      has_subfolders:S.hasSubfolders,
      all_files:S.allFiles.map(f=>({path:f.path,name:f.name,relPath:f.relPath,folder:f.folder}))
    })).json();
    if(!r.ok){alert(r.error);return;}
    S.progressOwner='batch';S.batchPollId=setInterval(pollBatch,500);
    S.batch.running=true;S.batch.phase='clean';render();
  }catch(e){alert(e.message);}
}

async function pollBatch(){
  try{
    const d=await apiGet('/api/batch/status');
    const wasRunning=S.batch.running;
    const changed=d.current!==S.batch.current||d.phase!==S.batch.phase||d.running!==S.batch.running||d.log?.length!==S.batch.log?.length;
    S.batch=d;
    if(d.running)S.progressOwner='batch';
    if(d.phase==='done_detect'){
      S.detections=d.detections||{};
      if(curFile()&&S.detections[curFile().path]){curFile()._maskData=null;}
    }
    if(!d.running&&S.batchPollId){clearInterval(S.batchPollId);S.batchPollId=null;
      if(d.phase==='done_detect')setTimeout(loadCurrentImage,50);
      if(d.phase==='done_clean'){
        Object.keys(S.detections).forEach(p=>S.cleanedPaths[p]=Date.now());
        if(d.corrections_count>0&&!S.hideFinetunePopup){
          S.showFinetunePopup=true;
          S.finetuneCorrections=d.corrections_count;
        }
      }
      render(); // Full render on completion
      return;
    }
    if(d.running&&!S.batchPollId){S.batchPollId=setInterval(pollBatch,500);}
    if(!wasRunning&&d.running){render();}else if(changed){_patchBatchUI();}
  }catch(e){console.error(e);}
}
function _patchBatchUI(){
  // Incrementally update batch progress without full render
  const d=S.batch;
  const bar=document.getElementById('batchBar');
  if(bar)bar.style.width=d.total>0?Math.round(d.current/d.total*100)+'%':'0%';
  const info=document.getElementById('batchInfo');
  if(info)info.textContent=d.running?`${d.phase}: ${d.current}/${d.total} \u00B7 ${d.currentFile||''}`:(d.phase||'');
  const logEl=document.getElementById('batchLog');
  if(logEl&&d.log){
    // Append only new log lines
    const existing=logEl.children.length;
    for(let i=existing;i<d.log.length;i++){
      const line=document.createElement('div');line.textContent=d.log[i];logEl.append(line);
    }
    logEl.scrollTop=logEl.scrollHeight;
  }
}

async function startAutonomous(){
  if(S.autonomous.running){await stopAutonomous();return;}
  if(!S.outputDir){alert(t('clean.no_export_dir'));return;}
  if(!S.allFiles.length)return;
  try{
    const multipleSources=S.cleanSources.length>1;
    const r=await(await apiPost('/api/autonomous/start',{
      files:S.allFiles.map(f=>({path:f.path,name:f.name,
        relPath:multipleSources?`${f._sourceLabel}/${f.relPath}`:f.relPath,
        outputPrefix:multipleSources?f._sourceLabel:'',archiveTmp:f.archiveTmp||''})),
      root_dir:multipleSources?'':S.rootFolder,source_roots:S.cleanSources,output_dir:S.outputDir,margin:5,
      padding:S.maskPadding,method:S.cleanMethod,
      artifact_scan_bottom_percent:20
    })).json();
    if(!r.ok)throw new Error(r.error||t('clean.error','Error'));
    S.progressOwner='auto';S.autonomous.running=true;S.autonomous.phase='starting';S.autonomous.total=r.total||S.allFiles.length;
    if(S.autonomousPollId)clearInterval(S.autonomousPollId);
    S.autonomousPollId=setInterval(pollAutonomous,600);render();
  }catch(e){alert(e.message);}
}

async function stopAutonomous(){
  try{await apiPost('/api/autonomous/stop',{});S.status=t('autonomous.stopping','Stopping...');}catch(e){alert(e.message);}
}

async function pollAutonomous(){
  try{
    const d=await apiGet('/api/autonomous/status');
    const wasRunning=S.autonomous.running;
    const changed=d.current!==S.autonomous.current||d.phase!==S.autonomous.phase||d.running!==S.autonomous.running||d.log?.length!==S.autonomous.log?.length;
    S.autonomous=d;
    if(d.running)S.progressOwner='auto';
    if(!d.running&&S.autonomousPollId){clearInterval(S.autonomousPollId);S.autonomousPollId=null;render();return;}
    if(d.running&&!S.autonomousPollId)S.autonomousPollId=setInterval(pollAutonomous,600);
    if(!wasRunning&&d.running)render();else if(changed)_patchAutonomousUI();
  }catch(e){console.error(e);}
}

function _patchAutonomousUI(){
  const d=S.autonomous;
  const bar=document.getElementById('batchBar');
  if(bar)bar.style.width=(d.progress!=null?d.progress:(d.total?Math.round(d.current/d.total*100):0))+'%';
  const info=document.getElementById('batchInfo');
  if(info)info.textContent=`${d.current||0}/${d.total||0} · ${d.currentFile||''}`;
  const logEl=document.getElementById('batchLog');
  if(logEl&&d.log){
    const existing=logEl.children.length;
    for(let i=existing;i<d.log.length;i++){const line=document.createElement('div');line.textContent=d.log[i];logEl.append(line);}
    logEl.scrollTop=logEl.scrollHeight;
  }
}

// Encoding-normalized comment.
async function loadModelFile(){
  try{const r=await(await apiPost('/api/browse-file',{filetypes:[["YOLO Model","*.pt"]]})).json();
    if(r.path){const lr=await(await apiPost('/api/load-model',{path:r.path})).json();if(lr.ok){S.backend.modelLoaded=true;S.status='Model loaded';}else alert(lr.error);render();}
  }catch(e){alert(e.message);}
}

// Encoding-normalized comment.
async function browseFolder(field){try{const r=await(await apiPost('/api/browse-folder',{})).json();if(r.path){S[field]=r.path;render();}}catch(e){alert(e.message);}}
async function browseModelFile(){try{const r=await(await apiPost('/api/browse-file',{filetypes:[["YOLO","*.pt"]]})).json();if(r.path){S.trainBaseModel=r.path;render();}}catch(e){alert(e.message);}}
async function startTraining(){
  if(S.trainStatus.training)return;
  const body={original_dir:S.trainOrigDir,cleaned_dir:S.trainCleanDir,epochs:S.trainEpochs,img_size:S.trainImgSize,base_model:S.trainBaseModel};
  try{const r=await(await apiPost('/api/train/start',body)).json();if(!r.ok){alert(r.error);return;}
    S.trainPollId=setInterval(pollTrain,1000);S.trainStatus.training=true;render();
  }catch(e){alert(e.message);}
}
async function startFinetune(){
  if(S.trainStatus.training)return;
  try{const body={epochs:S.finetuneEpochs,img_size:S.finetuneImgSize};
    if(S.finetuneDir)body.corrections_dir=S.finetuneDir;
    if(S.finetuneModel)body.base_model=S.finetuneModel;
    const r=await(await apiPost('/api/train/finetune',body)).json();if(!r.ok){alert(r.error);return;}
    S.trainPollId=setInterval(pollTrain,1000);S.trainStatus.training=true;render();
  }catch(e){alert(e.message);}
}
async function pollTrain(){try{const d=await apiGet('/api/train/status');
  const wasTraining=S.trainStatus?.training;
  S.trainStatus=d;
  if(!d.training&&S.trainPollId){clearInterval(S.trainPollId);S.trainPollId=null;checkBackend();render();return;}
  _patchTrainUI();
  }catch(e){console.error(e);}}
function _patchTrainUI(){
  const d=S.trainStatus;if(!d)return;
  const bar=document.getElementById('trainBar');
  if(bar)bar.style.width=(d.progress||0)+'%';
  const info=document.getElementById('trainInfo');
  if(info)info.textContent=d.training?`Р­РїРѕС…Р° ${d.epoch_current||0}/${d.epochs_total||0}`:(d.phase||'');
  const logEl=$('trainLog');
  if(logEl&&d.log){
    const existing=logEl.children.length;
    for(let i=existing;i<d.log.length;i++){
      const line=document.createElement('div');line.textContent=d.log[i];logEl.append(line);
    }
    logEl.scrollTop=logEl.scrollHeight;
  }
}

// Encoding-normalized comment.
const ICO={
  brush:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M18.37 2.63a2.12 2.12 0 013 3L14 13l-4 1 1-4 7.37-7.37z"/><path d="M7 7H4a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-3"/></svg>',
  eraser:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M20 20H7l-4-4a1 1 0 010-1.41l9.59-9.59a2 2 0 012.82 0l4.59 4.59a2 2 0 010 2.82L14 18.41"/><line x1="18" y1="13" x2="11" y2="20"/></svg>',
  rect:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M3 9h18M9 3v18" stroke-dasharray="2 2" opacity=".4"/></svg>',
  wand:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M3 21l10-10M15 3l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"/><path d="M20 8l.5 1 1 .5-1 .5-.5 1-.5-1-1-.5 1-.5L20 8z" opacity=".6"/><path d="M8 4l.5 1 1 .5-1 .5L8 7l-.5-1-1-.5 1-.5L8 4z" opacity=".4"/></svg>',
  eye:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  trash:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 002 2h8a2 2 0 002-2l1-12M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>',
  play:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><polygon points="6,4 20,12 6,20" fill="currentColor" opacity=".15"/><polygon points="6,4 20,12 6,20"/></svg>',
  settings:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
  left:'<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>',
  right:'<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>',
  folder:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z" fill="currentColor" opacity=".08"/><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>',
  model:'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity=".08"/><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>',
};
function icon(n){return ICO[n]||'';}

// Custom slider with fill track
function slider(opts){
  // opts: {min,max,step,value,onInput,width}
  const wrap=h('div',{className:'slider-wrap',style:{width:opts.width||'5rem'}});
  const fill=h('div',{className:'slider-fill'});
  const inp=h('input',{type:'range',min:String(opts.min||0),max:String(opts.max||100),
    step:String(opts.step||1),value:String(opts.value||0),style:{width:'100%'},
    onInput:e=>{
      _updateFill(inp,fill);
      if(opts.onInput) opts.onInput(e);
    }});
  wrap.append(fill,inp);
  requestAnimationFrame(()=>_updateFill(inp,fill));
  return wrap;
}
function _updateFill(inp,fill){
  const min=parseFloat(inp.min)||0,max=parseFloat(inp.max)||100,val=parseFloat(inp.value)||0;
  const pct=((val-min)/(max-min))*100;
  fill.style.width=pct+'%';
}


/**
 * Encoding-normalized comment.
 *
 * opts: array of {value, label} OR {group, items:[{value,label},...]}
 * options: { value, onChange, style, menuMaxHeight }
 */
function mkCustomSelect(opts, {value: initVal='', onChange, style={}, label=''}={}) {
  const root=h('select',{className:'conv-select',style:{minWidth:0,...style},
    'aria-label':label||t('ui.choose','Choose'), 'data-focus-key':label||opts.map(o=>o.group||o.value).join('|')});
  opts.forEach(o=>{
    const parent=o.items?h('optgroup',{label:o.group}):root;
    (o.items||[o]).forEach(item=>parent.append(h('option',{value:item.value,disabled:!!item.disabled},item.label||item.value)));
    if(o.items)root.append(parent);
  });
  root.value=initVal;
  root.addEventListener('change',()=>{if(onChange)onChange(root.value);});
  root._getValue=()=>root.value;
  root._setValue=value=>{root.value=value;};
  return root;
}

// Encoding-normalized comment.
function _restoreSidebarScroll(tree,tab,previousScroll){
  if(!tree)return;
  const prefix=tab==='convert'?'_conv':'_clean';
  const navKey=tab==='convert'?'_convNavByKey':'_navByKey';
  const topKey=prefix+'ScrollTop';
  const targetKey=prefix+'ScrollToKey';
  // Restore while the new tree is connected, before another render can
  // capture its default zero. No deferred write can override manual scrolling.
  tree.scrollTop=S[topKey]!=null?S[topKey]:previousScroll;
  S[topKey]=null;
  const toggled=S[targetKey]?tree.querySelector('[data-key="'+S[targetKey]+'"]'):null;
  if(toggled){
    toggled.scrollIntoView({block:'nearest',behavior:'auto'});
    S[targetKey]=null;
  }else if(S[navKey]){
    const active=tree.querySelector('.file-item.active');
    if(active)active.scrollIntoView({block:'nearest',behavior:'auto'});
    S[navKey]=false;
  }
}
let _convLiveSync=null;
function render(){
  if(String(S.convPreviewVariant||'auto').toLowerCase()!=='auto'){
    S.convPreviewVariant='auto';
    _invalidateCropCaches();
  }
  // Persist conv settings
  _convPersistKeys.forEach(k=>{localStorage.setItem('mcs_'+k,String(S[k]));});
  localStorage.setItem('mcs_convAutoBalanceMode',String(parseInt(S.convAutoBalanceMode)||0));
  localStorage.setItem('mcs_convAutoBalanceMargins',String((parseInt(S.convAutoBalanceMode)||0)===1));
  localStorage.setItem('mcs_convAutoBalanceMarginPx',String(parseInt(S.convAutoBalanceMarginPx)||0));
  localStorage.setItem('mcs_convAutoBalanceMarginUnit',String(S.convAutoBalanceMarginUnit||'px'));
  localStorage.setItem('mcs_convAutoBalanceMarginPct',String(parseFloat(S.convAutoBalanceMarginPct)||0));
  if(S.convProfile)localStorage.setItem('mcs_convProfile',S.convProfile);
  if(S.convFormat)localStorage.setItem('mcs_convFormat',S.convFormat);
  localStorage.setItem('mcs_convPreviewVariant','auto');
  localStorage.setItem('mcs_convBookmarks',JSON.stringify(S.convBookmarks||{}));
  localStorage.setItem('mcs_convAutoBmSuppressed',JSON.stringify(S.convAutoBmSuppressed||{}));
  localStorage.setItem('mcs_convBookmarkOrigin',JSON.stringify(S.convBookmarkOrigin||{}));
  localStorage.setItem('mcs_tab',S.tab);
  // Persist sources across F5
  sessionStorage.setItem('mcs_cleanSources',JSON.stringify(S.cleanSources));
  sessionStorage.setItem('mcs_convSources',JSON.stringify(S.convSources));
  sessionStorage.setItem('mcs_idx',String(S.idx));
  sessionStorage.setItem('mcs_cleanViewOpen',S.cleanViewOpen?'true':'false');
  if(S.convViewIdx!==null)sessionStorage.setItem('mcs_convViewIdx',String(S.convViewIdx));
  else sessionStorage.removeItem('mcs_convViewIdx');
  if(S.convExpandedSource)sessionStorage.setItem('mcs_convExpandedSource',S.convExpandedSource);
  else sessionStorage.removeItem('mcs_convExpandedSource');
  // Persist unsaved sidecar data across F5
  sessionStorage.setItem('mcs_convExclusions',JSON.stringify(S.convExclusions));
  sessionStorage.setItem('mcs_convExcluded',JSON.stringify(S.convExcluded));
  sessionStorage.setItem('mcs_convCustomCrop',JSON.stringify(S.convCustomCrop));
  sessionStorage.setItem('mcs_convCustomSplit',JSON.stringify(S.convCustomSplit));
  sessionStorage.setItem('mcs_convExtraMargin',JSON.stringify(S.convExtraMargin));
  sessionStorage.setItem('mcs_convEditOps',JSON.stringify(S.convEditOps));
  sessionStorage.setItem('mcs_convWatermarkMatches',JSON.stringify(S.convWatermarkMatches||{}));
  sessionStorage.setItem('mcs_convWatermarkReviewed',JSON.stringify(S.convWatermarkReviewed||{}));
  // Save scroll position before re-render
  const oldTree=document.querySelector('.file-tree');
  const savedTreeScroll=oldTree?oldTree.scrollTop:0;
  const oldCa=document.querySelector('.canvas-area');
  if(oldCa){
    S._convCanvasScroll=oldCa.scrollTop;
    S._convCanvasW=oldCa.clientWidth||0;
    S._convCanvasH=oldCa.clientHeight||0;
  }
  _convLiveSync=null;

  const app=$('app');const restoreFocus=captureAppFocus(app);app.innerHTML='';
  const b=S.backend;

  // Header
  const hdr=h('div',{className:'header'},
    h('div',{className:'logo'},h('span',{className:'logo-text',innerHTML:'<svg height="100%" viewBox="0 0 80 24" fill="none"><defs><linearGradient id="lg" x1="0" y1="0" x2="80" y2="24" gradientUnits="userSpaceOnUse"><stop stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent2)"/></linearGradient></defs><text x="0" y="19" font-family="system-ui,-apple-system,sans-serif" font-size="22" font-weight="700" fill="url(#lg)" letter-spacing="-0.5">MA</text><path d="M38 3.5 L43.5 19 L40 19 L34.5 3.5Z" fill="url(#lg)"/><text x="45" y="19" font-family="system-ui,-apple-system,sans-serif" font-size="22" font-weight="700" fill="url(#lg)" letter-spacing="-0.5">C</text></svg>'})),
    h('div',{style:{display:'flex',gap:'0',alignItems:'center'}},
      // Tab buttons inside header
      h('nav',{style:{display:'flex',background:'rgba(255,255,255,0.04)',padding:'3px',borderRadius:'10px',marginRight:'0.6rem'}},
        h('button',{className:'header-tab'+(S.tab==='clean'?' active':''),
          style:{background:S.tab==='clean'?'rgba(255,255,255,0.08)':'transparent',color:S.tab==='clean'?'var(--text)':'var(--text3)',
          boxShadow:S.tab==='clean'?'0 2px 8px rgba(0,0,0,0.2)':'none'},
          onClick:()=>{S.tab='clean';render();setTimeout(loadCurrentImage,30);}},t('tabs.clean')),
        h('button',{className:'header-tab'+(S.tab==='train'?' active':''),
          style:{background:S.tab==='train'?'rgba(255,255,255,0.08)':'transparent',color:S.tab==='train'?'var(--text)':'var(--text3)',
          boxShadow:S.tab==='train'?'0 2px 8px rgba(0,0,0,0.2)':'none'},
          onClick:()=>{S.tab='train';render();}},t('tabs.train')),
        (()=>{
          if(!S.convAvailable)return null;
          const btn=h('button',{className:'header-tab'+(S.tab==='convert'?' active':''),
            style:{background:S.tab==='convert'?'rgba(255,255,255,0.08)':'transparent',color:S.tab==='convert'?'var(--text)':'var(--text3)',
            boxShadow:S.tab==='convert'?'0 2px 8px rgba(0,0,0,0.2)':'none',display:'flex',alignItems:'center',gap:'4px'},
            onClick:()=>{S.tab='convert';render();}});
          const kccImg=document.createElement('img');
          kccImg.src=_KCC_ICON;
          Object.assign(kccImg.style,{width:'14px',height:'14px',borderRadius:'3px'});
          btn.append(kccImg,t('tabs.convert'));
          return btn;
        })()
      ),
      h('button',{className:'tool-btn'+(S.showSettings?' active':''),'aria-label':t('settings.title'),'aria-expanded':String(!!S.showSettings),style:{width:'2.2rem',height:'2.2rem'},
        onClick:()=>{S.showSettings=!S.showSettings;render();setTimeout(loadCurrentImage,30);},
        innerHTML:S.showSettings?'<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>':icon('settings')}))
  );
  app.append(hdr);

  // Settings panel (anchored to header right, drops down)
  if(S.showSettings){
    const cpuOpt=h('button',{className:'device-opt'+(b.device==='cpu'?' active cpu-sel':''),onClick:()=>setDevice('cpu')},h('span',{className:'dev-label'},'\uD83D\uDDA5 CPU'),h('span',{className:'dev-name'},b.cpu||'CPU'));
    const gpuOpt=h('button',{className:'device-opt'+(b.device==='cuda'?' active gpu':'')+(!b.cudaAvailable?' disabled':''),onClick:()=>{if(b.cudaAvailable)setDevice('cuda');}},h('span',{className:'dev-label'},b.cudaAvailable?'\u26A1 GPU':'\u26A1 GPU (N/A)'),h('span',{className:'dev-name'},b.cudaAvailable?(b.gpu||'CUDA'):'Not detected'));

    const sp=h('div',{className:'settings-panel',style:{position:'fixed',top:'3.2rem',right:'0.5rem',zIndex:'200'}});
    sp.append(h('div',{className:'settings-title'},t('settings.title')));

    // Device section
    sp.append(h('div',{className:'settings-section-label'},t('settings.device')));
    sp.append(h('div',{className:'device-switcher',style:{marginBottom:'0.6rem',width:'100%'}},cpuOpt,gpuOpt));

    // Model section
    sp.append(h('div',{className:'settings-section-label'},t('settings.model')));
    sp.append(h('button',{className:'settings-model-btn',onClick:loadModelFile,innerHTML:icon('model')+' <span>'+t('settings.load_model')+'</span>'}));

    sp.append(h('div',{style:{height:'1px',background:'var(--glass-border)',margin:'0.6rem 0'}}));

    // Clean method
    sp.append(h('div',{className:'settings-row'},h('label',null,t('settings.clean_method')),
      (()=>{
        const wrap=h('div',{className:'seg-control'});
        [['white','White'],['inpaint','Inpaint'],['lama','LaMa']].forEach(([v,t])=>{
          wrap.append(h('button',{className:'seg-btn'+(S.cleanMethod===v?' active':''),onClick:()=>{S.cleanMethod=v;try{localStorage.setItem('mcs_cleanMethod',S.cleanMethod);}catch(ex){}render();setTimeout(loadCurrentImage,30);}},t));
        });return wrap;})()));

    sp.append(h('div',{className:'settings-row'},h('label',null,t('settings.confidence')),
      h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
        slider({min:0.1,max:0.9,step:0.05,value:S.confidence,onInput:e=>{S.confidence=+e.target.value;$('confL').textContent=S.confidence.toFixed(2);try{localStorage.setItem('mcs_confidence',S.confidence);}catch(ex){}}}),
        h('span',{id:'confL',style:{fontSize:'0.8rem',color:'var(--text2)'}},S.confidence.toFixed(2)))));

    sp.append(h('div',{className:'settings-row'},h('label',null,t('settings.mask_padding')),
      h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
        slider({min:0,max:15,step:1,value:S.maskPadding,onInput:e=>{S.maskPadding=+e.target.value;$('padL').textContent=S.maskPadding;try{localStorage.setItem('mcs_maskPadding',S.maskPadding);}catch(ex){}}}),
        h('span',{id:'padL',style:{fontSize:'0.8rem',color:'var(--text2)'}},String(S.maskPadding)))));

    sp.append(h('div',{style:{height:'1px',background:'var(--glass-border)',margin:'0.6rem 0'}}));

    // Language switcher
    sp.append(h('div',{className:'settings-row'},h('label',null,t('settings.language')),
      (()=>{
        if(_availLangs.length<=2){
          const wrap=h('div',{className:'seg-control'});
          _availLangs.forEach(v=>{
            wrap.append(h('button',{className:'seg-btn'+(_langCode===v?' active':''),onClick:async()=>{await _loadLang(v);render();}},v.toUpperCase()));
          });return wrap;
        } else {
          const sel=mkCustomSelect(
            _availLangs.map(v=>({value:v,label:v.toUpperCase()})),
            {value:_langCode, style:{minWidth:'5rem'}, onChange:async v=>{await _loadLang(v);render();}}
          );return sel;
        }
      })()));

    // Encoding-normalized comment.
    app.append(sp);
  }

  if(S.tab==='clean') renderClean(app);
  else if(S.tab==='convert'&&S.convAvailable) renderConvert(app);
  else renderTrain(app);
  if(restoreFocus)restoreFocus();
  if(S.tab==='clean'||S.tab==='convert'){
    _restoreSidebarScroll(document.querySelector('.file-tree'),S.tab,savedTreeScroll);
  }
}

function renderArtifactProfileOverlays(app){
  const overlayStyle={position:'fixed',inset:0,background:'rgba(0,0,0,.64)',backdropFilter:'blur(8px)',zIndex:350,
    display:'flex',alignItems:'center',justifyContent:'center'};
  const panelStyle={background:'var(--bg2)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
    width:'min(31rem,92vw)',maxHeight:'82vh',overflow:'auto',padding:'1.25rem',boxShadow:'0 24px 80px rgba(0,0,0,.55)'};
  const inputStyle={width:'100%',boxSizing:'border-box',background:'rgba(255,255,255,.045)',border:'1px solid var(--glass-border)',
    borderRadius:'7px',color:'var(--text)',padding:'.48rem .58rem',fontSize:'.75rem',outline:'none'};
  const buttonStyle={padding:'.48rem .85rem',borderRadius:'7px',fontSize:'.75rem',fontWeight:'600',cursor:'pointer'};
  if(S.artifactDraft){
    const draft=S.artifactDraft,overlay=h('div',{style:overlayStyle});
    const panel=h('div',{style:panelStyle});
    panel.append(h('div',{style:{fontSize:'1rem',fontWeight:'700',marginBottom:'.25rem'}},
      t('artifacts.add_title','Add a reusable sample')));
    panel.append(h('div',{style:{fontSize:'.7rem',color:'var(--text3)',lineHeight:'1.45',marginBottom:'.75rem'}},
      t('artifacts.action_desc','Choose what maic should do when similar content is found.')));
    const actionRow=h('div',{style:{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'.5rem',marginBottom:'.85rem'}});
    const actionButton=(action,label,description,color)=>h('button',{type:'button',style:{textAlign:'left',padding:'.65rem .7rem',borderRadius:'8px',cursor:'pointer',
      color:'var(--text)',background:draft.action===action?color:'var(--glass2)',border:draft.action===action?'1px solid currentColor':'1px solid var(--glass-border)'},
      onClick:()=>{if(draft.action!==action){draft.action=action;render();setTimeout(loadCurrentImage,30);}}},
      h('div',{style:{fontSize:'.74rem',fontWeight:'700'}},label),h('div',{style:{fontSize:'.61rem',color:'var(--text3)',marginTop:'3px',lineHeight:'1.3'}},description));
    actionRow.append(
      actionButton('remove',t('artifacts.action_remove','Remove matches'),t('artifacts.action_remove_desc','maic removes matches on a uniform background and ignores confirmed perimeter matches when calculating the crop.'),'rgba(168,85,247,.16)'),
      actionButton('exclude',t('artifacts.action_protect','Protect matches'),t('artifacts.action_protect_desc','Matching content is never removed as a logo or page number.'),'rgba(245,158,11,.14)'));
    panel.append(actionRow);
    const compatible=S.artifactProfiles.filter(profile=>profile.action===draft.action);
    const profileSelect=h('select',{style:inputStyle});
    profileSelect.append(h('option',{value:''},t('artifacts.new_profile','New profile')));
    compatible.forEach(profile=>profileSelect.append(h('option',{value:profile.id},`${profile.label} (${profile.referenceCount})`)));
    const nameInput=h('input',{style:{...inputStyle,marginTop:'.55rem'},value:draft.action==='exclude'?t('artifacts.default_exclusion','Protected content'):t('artifacts.default_logo','Logo'),maxlength:80});
    const thresholdInput=h('input',{type:'number',min:'0.70',max:'0.99',step:'0.01',value:'0.88',style:{...inputStyle,marginTop:'.55rem'}});
    profileSelect.onchange=()=>{
      const selected=S.artifactProfiles.find(profile=>profile.id===profileSelect.value);
      if(selected){nameInput.value=selected.label;thresholdInput.value=Number(selected.threshold||.88).toFixed(2);nameInput.disabled=true;}
      else{nameInput.disabled=false;}
    };
    panel.append(h('div',{style:{fontSize:'.65rem',color:'var(--text2)',marginBottom:'.25rem'}},t('artifacts.profile','Profile')),profileSelect);
    panel.append(h('div',{style:{fontSize:'.65rem',color:'var(--text2)',marginTop:'.65rem'}},t('artifacts.name','Name')),nameInput);
    panel.append(h('div',{style:{fontSize:'.65rem',color:'var(--text2)',marginTop:'.65rem'}},t('artifacts.threshold','Similarity threshold')),thresholdInput);
    panel.append(h('div',{style:{fontSize:'.62rem',color:'var(--text3)',marginTop:'.55rem'}},
      `${t('artifacts.area','Selected area')}: ${draft.box[2]-draft.box[0]} × ${draft.box[3]-draft.box[1]} px`));
    const buttons=h('div',{style:{display:'flex',justifyContent:'flex-end',gap:'.55rem',marginTop:'1rem'}});
    buttons.append(h('button',{style:{...buttonStyle,background:'var(--glass2)',border:'1px solid var(--glass-border)',color:'var(--text2)'},
      onClick:cancelArtifactCapture},t('clean.cancel','Cancel')));
    buttons.append(h('button',{disabled:S.artifactSaving,style:{...buttonStyle,background:'linear-gradient(135deg,var(--accent),var(--accent2))',border:'none',color:'#fff'},
      onClick:()=>saveArtifactDraft(profileSelect.value,nameInput.value,thresholdInput.value)},S.artifactSaving?t('artifacts.saving','Saving...'):t('artifacts.save','Save profile')));
    panel.append(buttons);overlay.append(panel);app.append(overlay);
  }else if(S.showArtifactProfiles){
    const overlay=h('div',{style:overlayStyle,onClick:e=>{if(e.target===overlay){S.showArtifactProfiles=false;render();setTimeout(loadCurrentImage,30);}}});
    const panel=h('div',{style:panelStyle});
    panel.append(h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'.8rem'}},
      h('div',{style:{fontSize:'1rem',fontWeight:'700'}},t('artifacts.manage','Artifact profiles')),
      h('button',{style:{background:'none',border:'none',color:'var(--text3)',fontSize:'1.15rem',cursor:'pointer'},onClick:()=>{S.showArtifactProfiles=false;render();setTimeout(loadCurrentImage,30);}},'×')));
    if(!S.artifactProfiles.length){
      panel.append(h('div',{style:{fontSize:'.75rem',color:'var(--text3)',padding:'1rem 0'}},t('artifacts.empty','No profiles yet. Select Add sample, then draw a rectangle.')));
    }else S.artifactProfiles.forEach(profile=>{
      const color=profile.action==='exclude'?'#f59e0b':'#a855f7';
      panel.append(h('div',{style:{display:'flex',alignItems:'center',gap:'.7rem',padding:'.65rem .7rem',marginBottom:'.45rem',background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'8px'}},
        h('span',{style:{width:'.55rem',height:'.55rem',borderRadius:'50%',background:color,flex:'0 0 auto'}}),
        h('div',{style:{flex:'1',minWidth:0}},h('div',{style:{fontSize:'.76rem',fontWeight:'600',overflow:'hidden',textOverflow:'ellipsis'}},profile.label),
          h('div',{style:{fontSize:'.61rem',color:'var(--text3)',marginTop:'2px'}},`${profile.action==='exclude'?t('artifacts.exclusion','Exclusion'):t('artifacts.removable','Removable')} · ${profile.referenceCount} · ${Number(profile.threshold).toFixed(2)}`)),
        h('button',{style:{background:'none',border:'none',color:'var(--red)',fontSize:'.7rem',cursor:'pointer'},onClick:()=>deleteArtifactProfile(profile.id)},t('ui.delete','Delete'))));
    });
    overlay.append(panel);app.append(overlay);
  }
}

function renderClean(app){
  const b=S.backend;
  const body=h('div',{className:'body'});

  // Sidebar
  const sb=h('div',{className:'sidebar'});

  if(S.cleanSources.length>0||S.allFiles.length>0){
    const sbh=h('div',{className:'sidebar-hdr'});
    // Title row with count badge, add and close
    const titleRow=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'0.5rem'}});
    const titleLeft=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem'}});
    titleLeft.append(h('span',{style:{fontSize:'0.75rem',fontWeight:'600',color:'var(--text)'}},t('files')));
    if(S.allFiles.length>0){
      titleLeft.append(h('span',{style:{fontSize:'0.65rem',fontWeight:'600',color:'var(--accent)',background:'rgba(110,170,255,0.12)',
        padding:'0.1rem 0.4rem',borderRadius:'10px'}},String(S.allFiles.length)));
    }
    titleRow.append(titleLeft);
    const titleBtns=h('div',{style:{display:'flex',gap:'0.3rem'}});
    titleBtns.append(h('button',{style:{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',color:'var(--text2)',fontSize:'0.7rem',transition:'all .2s'},
      onClick:showCleanSourceModal,title:t('files.add_source')},'+'));
    titleBtns.append(h('button',{style:{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',color:'var(--text3)',transition:'all .2s'},
      onClick:()=>{S.cleanSources=[];S.rootFolder='';S.outputDir='';S.groups=[];S.allFiles=[];S.idx=0;S.detections={};S.cleanedPaths={};S.cleanCollapsed={};S.status='';render();},
      onMouseover:function(){this.style.color='var(--red)';this.style.borderColor='rgba(248,113,113,0.3)';},
      onMouseout:function(){this.style.color='var(--text3)';this.style.borderColor='var(--glass-border)';},
      title:t('files.clear_all'),innerHTML:'<svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'}));
    titleRow.append(titleBtns);
    sbh.append(titleRow);

    // Source paths as pills
    S.cleanSources.forEach((s,i)=>{
      const name=s.split(/[/\\]/).filter(Boolean).slice(-2).join('/');
      const isDir=!s.match(/\.\w{2,4}$/);
      const pill=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.3rem 0.5rem',
        background:'var(--glass2)',borderRadius:'var(--radius-xs)',border:'1px solid var(--glass-border)',marginBottom:'0.25rem',cursor:'pointer',transition:'all .2s'},
        title:s,
        onMouseover:function(){this.style.borderColor='rgba(110,170,255,0.3)';},
        onMouseout:function(){this.style.borderColor='var(--glass-border)';}});
      pill.append(h('span',{innerHTML:isDir?'<svg width="12" height="12" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>':'<svg width="12" height="12" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6M9 13h4"/></svg>'}));
      pill.append(h('span',{style:{fontSize:'0.68rem',color:'var(--text2)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:'1'}},name));
      pill.append(h('span',{style:{fontSize:'0.55rem',color:'var(--text3)',cursor:'pointer',padding:'0 0.1rem'},
        onClick:e=>{e.stopPropagation();S.cleanSources.splice(i,1);loadCleanSources();},
        onMouseover:function(){this.style.color='var(--red)';},
        onMouseout:function(){this.style.color='var(--text3)';}},'\u2715'));
      sbh.append(pill);
    });

    // Export path pill
    const outName=S.outputDir?S.outputDir.split(/[/\\]/).filter(Boolean).slice(-2).join('/'):t('export.not_set');
    const outPill=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.3rem 0.5rem',
      background:'rgba(52,211,153,0.06)',borderRadius:'var(--radius-xs)',border:'1px solid rgba(52,211,153,0.15)',cursor:'pointer',transition:'all .2s'},
      title:S.outputDir||t('export.select_folder'),onClick:selectOutputFolder,
      onMouseover:function(){this.style.borderColor='rgba(52,211,153,0.35)';},
      onMouseout:function(){this.style.borderColor='rgba(52,211,153,0.15)';}});
    outPill.append(h('span',{innerHTML:'<svg width="12" height="12" fill="none" stroke="#34d399" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>'}));
    outPill.append(h('span',{style:{fontSize:'0.68rem',color:'var(--green)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:'1',opacity:S.outputDir?1:0.5}},outName));
    outPill.append(h('span',{style:{fontSize:'0.6rem',color:'var(--text3)',flexShrink:'0'}},'\u270e'));
    sbh.append(outPill);
    sb.append(sbh);
  }

  if(S.allFiles.length===0){
    const dz=h('button',{className:'sidebar-dropzone',onClick:showCleanSourceModal});
    dz.innerHTML='<svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24" style="color:var(--text3);margin-bottom:0.6rem"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z" stroke-linecap="round"/><path d="M12 10v6M9 13h6" stroke-linecap="round"/></svg>';
    dz.append(h('div',{style:{fontSize:'0.8rem',color:'var(--text2)',fontWeight:'500'}},t('files.add_source')));
    dz.append(h('div',{style:{fontSize:'0.65rem',color:'var(--text3)',marginTop:'0.3rem'}},t('files.folder_or_archive')));
    sb.append(dz);
  } else {
    const tree=h('div',{className:'file-tree'});

    // Encoding-normalized comment.
    if(S.allFiles.length===0){
      const scanning = S.status===t('clean.scanning');
      tree.append(h('div',{style:{padding:'1rem',fontSize:'0.7rem',color:'var(--text3)',textAlign:'center'}},
        scanning
          ? h('div',null,
              h('div',{style:{marginBottom:'0.4rem',fontSize:'0.8rem'}}, 'вЏі'),
              t('clean.scanning','Scanning...')
            )
          : h('div',null,
              h('div',{style:{marginBottom:'0.4rem',fontSize:'0.8rem'}}, '\u26A0'),
              S.status || t('clean.no_images','No images found')
            )
      ));
    }

    let fileIdx=0;
    // Group files by source
    S.cleanSources.forEach((src,si)=>{
      const srcName=src.split(/[/\\]/).filter(Boolean).slice(-1)[0];
      const srcKey='src:'+si;
      const srcOpen=!S.cleanCollapsed[srcKey];
      // Count files from this source
      const srcFiles=[];
      S.groups.forEach(g=>{
        g.files.forEach(f=>{if(f.path.startsWith(src)||S.cleanSources.length===1)srcFiles.push(f);});
      });

      // Source header (collapsible)
      const srcHdr=h('div',{className:'group-header','data-key':srcKey,style:{cursor:'pointer',fontWeight:'600'},
        onClick:()=>{
          const ft=document.querySelector('.file-tree');
          if(ft)S._cleanScrollTop=ft.scrollTop;
          S._cleanScrollToKey=srcKey;
          S.cleanCollapsed[srcKey]=srcOpen;
          render();
        }});
      srcHdr.append(h('span',{className:'g-icon',style:{fontSize:'0.6rem',transition:'transform .15s',
        display:'inline-block',transform:srcOpen?'rotate(90deg)':'rotate(0deg)'}},'\u25B6'));
      const isDir=!src.match(/\.\w{2,4}$/);
      srcHdr.append(h('span',{style:{fontSize:'0.8rem'}},isDir?'\ud83d\udcc1':'\ud83d\udce6'));
      srcHdr.append(h('span',{style:{flex:'1',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},srcName));
      const srcFileCount=S.cleanSources.length===1?S.allFiles.length:srcFiles.length;
      if(srcFileCount)srcHdr.append(h('span',{className:'group-count'},'('+srcFileCount+')'));
      tree.append(srcHdr);

      if(!srcOpen){
        // Skip files but still count
        S.groups.forEach(g=>{fileIdx+=g.files.length;});
        return;
      }

      // Show groups within this source
      S.groups.forEach((g,gi)=>{
      const gKey='cg:'+gi;
      const gOpen=!S.cleanCollapsed[gKey];
      // Group header - collapsible
      const ghdr=h('div',{className:'group-header',style:{cursor:'pointer',paddingLeft:'1rem'},'data-key':gKey,
        onClick:()=>{
          const ft=document.querySelector('.file-tree');
          if(ft)S._cleanScrollTop=ft.scrollTop;
          S._cleanScrollToKey=gKey;
          S.cleanCollapsed[gKey]=gOpen;render();
        }});
      ghdr.append(h('span',{className:'g-icon',style:{fontSize:'0.6rem',transition:'transform .15s',
        transform:gOpen?'rotate(90deg)':'rotate(0deg)'}},'\u25B6'));
      ghdr.append(h('span',{className:'g-icon',innerHTML:icon('folder')}));
      ghdr.append(h('span',{style:{flex:'1',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},g.folderName));
      ghdr.append(h('span',{className:'group-count'},'('+g.files.length+')'));
      tree.append(ghdr);

      if(gOpen){
        g.files.forEach(f=>{
          const idx=fileIdx++;
          const det=S.detections[f.path];
          const cleaned=S.cleanedPaths[f.path];
          let thumbSrc=API+'/api/serve-image?path='+encodeURIComponent(f.path);
          const _te=S.cleanedPaths[f.path]||(S._thumbEpoch&&S._thumbEpoch[f.path]);
          if(_te)thumbSrc+='&t='+_te;
          let detectText='', detectClass='none';
          if(cleaned){detectText='\u2713 '+t('clean.cleaned','Cleaned');detectClass='clean';}
          else if(det&&det._userMask){detectText='\u270E '+t('mask.manual','Manual mask');detectClass='found';}
          else if(det&&det.boxes&&det.boxes.length>0){detectText=det.boxes.length+' '+t('clean.artifacts_word','artifacts');detectClass='found';}
          const _isWideThumb=!!(S._wideThumbByPath&&S._wideThumbByPath[f.path]);

          tree.append(h('div',{className:'file-item'+(idx===S.idx?' active':'')+(_isWideThumb?' wide':''),
            style:{paddingLeft:'1.5rem'},
            onClick:()=>{if(_maskEditing)cancelMaskEdit();saveMask();resetView();S.idx=idx;S.cleanViewOpen=true;if(!S._thumbEpoch)S._thumbEpoch={};S._thumbEpoch[f.path]=Date.now();render();setTimeout(loadCurrentImage,30);}},
            h('img',{className:'file-thumb',src:thumbSrc,loading:'lazy',
              onLoad:function(){
                const isWide=_isWideSidebarThumb(this.naturalWidth,this.naturalHeight);
                if(!S._wideThumbByPath)S._wideThumbByPath={};
                S._wideThumbByPath[f.path]=isWide;
                const p=this.parentElement;
                if(p)p.classList.toggle('wide',isWide);
              }}),
            h('div',{className:'file-info'},
              h('div',{className:'file-name'},f.name),
              detectText?h('div',{className:'file-detect '+detectClass},detectText):null
            )
          ));
        });
      } else {
        fileIdx+=g.files.length;
      }
    });
    }); // end S.cleanSources.forEach
    sb.append(tree);
  }
  body.append(sb);

  // Main
  const main=h('div',{className:'main'});

  // Toolbar
  const tb=h('div',{className:'toolbar'});

  // Drawing tools group
  const drawGroup=h('div',{className:'tool-group'});
  [['brush',t('tools.brush')],['eraser',t('tools.eraser')],['rect',t('tools.rect')]].forEach(([t,title])=>{
    drawGroup.append(h('button',{className:'tool-btn'+(S.tool===t?' active':''),title,onClick:()=>{S.tool=t;render();setTimeout(loadCurrentImage,30);},innerHTML:icon(t)}));
  });
  drawGroup.append(h('div',{className:'tool-group-sep'}));
  const brushSizeBlock=h('div',{className:'brush-size-control'});
  brushSizeBlock.append(h('span',{className:'brush-size-label'},t('train.size_label')));
  brushSizeBlock.append(slider({min:2,max:100,value:S.brushSize,width:'6.2rem',onInput:e=>{S.brushSize=+e.target.value;$('bsL').textContent=S.brushSize;}}));
  brushSizeBlock.append(h('span',{id:'bsL',className:'brush-size-value'},String(S.brushSize)));
  drawGroup.append(brushSizeBlock);
  tb.append(drawGroup);

  // View tools group
  const viewGroup=h('div',{className:'tool-group'});
  viewGroup.append(h('button',{className:'tool-btn'+(S.showMask?' active':''),title:t('tools.mask'),onClick:()=>{S.showMask=!S.showMask;drawOverlay();render();setTimeout(loadCurrentImage,30);},innerHTML:icon('eye')}));
  viewGroup.append(h('button',{className:'tool-btn',title:t('tools.clear_mask'),onClick:clearMask,innerHTML:icon('trash')}));
  viewGroup.append(h('button',{className:'tool-btn',title:t('tools.refresh','Refresh preview'),onClick:()=>{
    const f=curFile();if(f){if(!S._thumbEpoch)S._thumbEpoch={};S._thumbEpoch[f.path]=Date.now();delete S.cleanedPaths[f.path];}
    render();setTimeout(loadCurrentImage,30);
  },innerHTML:'\u23F3'}));
  tb.append(viewGroup);

  const artifactGroup=h('div',{className:'tool-group'});
  artifactGroup.append(h('button',{className:'action-btn'+(S.artifactCapture?' active':''),
    style:{background:'rgba(110,170,255,.12)',border:'1px solid rgba(110,170,255,.28)'},
    title:t('artifacts.add_hint','Add an example of recurring content'),
    onClick:startArtifactCapture},'⊕ '+t('artifacts.add_sample','Add sample')));
  artifactGroup.append(h('button',{className:'tool-btn',title:t('artifacts.manage','Manage artifact profiles'),
    onClick:()=>{S.showArtifactProfiles=true;render();setTimeout(loadCurrentImage,30);}},String(S.artifactProfiles.length)));
  tb.append(artifactGroup);

  // Action buttons group — detect
  const d1=h('button',{className:'action-btn',style:{background:'var(--purple-bg)',border:'1px solid rgba(167,139,250,0.2)'},onClick:detectCurrent,innerHTML:icon('wand')+' '+t('toolbar.detect_here')});
  if(S.processing||!curFile()||b.status!=='connected')d1.disabled=true;tb.append(d1);

  const dAll=h('button',{className:'action-btn',style:{background:'rgba(110,170,255,0.12)',border:'1px solid rgba(110,170,255,0.2)'},onClick:batchDetect,innerHTML:icon('wand')+' '+t('toolbar.detect_all')});
  if(S.batch.running||S.autonomous.running||S.allFiles.length===0||b.status!=='connected')dAll.disabled=true;tb.append(dAll);

  tb.append(h('div',{className:'sep'}));

  // Action buttons group — clean
  const c1=h('button',{className:'action-btn',style:{background:'var(--orange-bg)',border:'1px solid rgba(251,146,60,0.2)'},onClick:cleanCurrent,innerHTML:icon('play')+' '+t('toolbar.clean_here')});
  if(S.processing||!curFile()||!S.cleanViewOpen||_maskEditing)c1.disabled=true;tb.append(c1);

  const detCount=Object.keys(S.detections).length;
  const cAll=h('button',{className:'action-btn',style:{background:'var(--green-bg)',border:'1px solid var(--green-border)'},onClick:batchClean,innerHTML:icon('play')+' '+t('toolbar.clean_all')+' ('+detCount+')'});
  if(S.batch.running||S.autonomous.running||detCount===0||_maskEditing)cAll.disabled=true;tb.append(cAll);

  tb.append(h('div',{className:'sep'}));
  const autoBtn=h('button',{className:'action-btn',style:{background:S.autonomous.running?'rgba(248,113,113,.14)':'linear-gradient(135deg,rgba(139,92,246,.22),rgba(59,130,246,.18))',border:S.autonomous.running?'1px solid rgba(248,113,113,.35)':'1px solid rgba(139,92,246,.35)'},
    onClick:startAutonomous,innerHTML:(S.autonomous.running?'■ ':'✦ ')+(S.autonomous.running?t('autonomous.stop','Stop auto'):t('autonomous.start','Autonomous · 5 px margins'))});
  if(!S.autonomous.running&&(S.batch.running||S.allFiles.length===0||!S.outputDir||b.status!=='connected'))autoBtn.disabled=true;
  tb.append(autoBtn);

  main.append(tb);

  const autoLog=Array.isArray(S.autonomous.log)?S.autonomous.log:[];
  const autoActive=S.autonomous.running||(S.progressOwner==='auto'&&autoLog.length>0);
  const progressState=autoActive?S.autonomous:S.batch;
  const batchLog=Array.isArray(progressState.log)?progressState.log:[];
  const hasBatchLog=batchLog.length>0;
  const showBatchLog=progressState.running||hasBatchLog;

  // Canvas area
  const ca=h('div',{className:'canvas-area'+(showBatchLog&&!S.cleanViewOpen?' clean-preview-stack':'')});

  if(curFile()&&S.cleanViewOpen){
    const cv=h('div',{className:'clean-viewer-layer'});
    cv.append(h('button',{className:'nav-btn',style:{left:'10px'},onClick:()=>{S._navByKey=true;navImage(-1);},innerHTML:icon('left')}));
    const cvs=h('canvas',{id:'mainCanvas',className:'main-canvas',
      style:{cursor:S.artifactCapture?'crosshair':((S.tool==='brush'||S.tool==='eraser')?'none':'crosshair'),transformOrigin:'center center',
        transform:S.viewScale!==1||S.viewX!==0||S.viewY!==0?`translate(${S.viewX}px,${S.viewY}px) scale(${S.viewScale})`:''},
      onMousedown:onMD,onMousemove:onMM,onMouseup:onMU,onMouseleave:onML,onWheel:onWheel,onContextmenu:e=>e.preventDefault()});
    cvs.addEventListener('mousedown',e=>{if(e.button===1)e.preventDefault();});
    cv.append(cvs);
    cv.append(h('canvas',{id:'maskCanvas',style:{display:'none'}}));
    cv.append(h('button',{className:'nav-btn',style:{right:'10px'},onClick:()=>{S._navByKey=true;navImage(1);},innerHTML:icon('right')}));
    cv.append(h('button',{style:{position:'absolute',top:'0.6rem',right:'0.8rem',zIndex:21,
      display:'flex',alignItems:'center',justifyContent:'center',gap:'0.3rem',height:'2rem',padding:'0 0.65rem',
      borderRadius:'999px',border:'1px solid rgba(255,255,255,0.12)',background:'rgba(15,15,20,0.75)',
      color:'rgba(255,255,255,0.78)',fontSize:'0.72rem',fontWeight:'600',cursor:'pointer',
      boxShadow:'0 4px 12px rgba(0,0,0,0.4)',backdropFilter:'blur(20px)',WebkitBackdropFilter:'blur(20px)',
      transition:'all .15s'},
      onClick:()=>{S.artifactCapture=null;S.artifactDraft=null;if(_maskEditing)cancelMaskEdit();else saveMask();S.cleanViewOpen=false;resetView();render();},
      onMouseover:function(){this.style.background='rgba(15,15,20,0.9)';this.style.color='#fff';},
      onMouseout:function(){this.style.background='rgba(15,15,20,0.75)';this.style.color='rgba(255,255,255,0.78)';}},'× '+t('close','Close')));
    // Editing overlay
    if(_maskEditing){
      const editBar=h('div',{style:{position:'absolute',top:'0.6rem',left:'50%',transform:'translateX(-50%)',zIndex:20,
        display:'flex',alignItems:'center',gap:'0.5rem',background:'rgba(15,15,20,0.8)',backdropFilter:'blur(20px)',
        border:'1px solid rgba(255,255,255,0.12)',borderRadius:'var(--radius)',padding:'0.4rem 0.8rem',boxShadow:'0 8px 24px rgba(0,0,0,0.5)',
        textShadow:'0 1px 3px rgba(0,0,0,0.5)'}});
      // Undo/Redo
      const undoBtn=h('button',{style:{background:'none',border:'none',color:_undoStack.length?'var(--accent)':'rgba(255,255,255,0.35)',
        fontSize:'0.85rem',cursor:_undoStack.length?'pointer':'default',padding:'0.2rem 0.4rem'},
        onClick:()=>{maskUndo();},title:t('tools.undo')},'\u21A9');
      const redoBtn=h('button',{style:{background:'none',border:'none',color:_redoStack.length?'var(--accent)':'rgba(255,255,255,0.35)',
        fontSize:'0.85rem',cursor:_redoStack.length?'pointer':'default',padding:'0.2rem 0.4rem'},
        onClick:()=>{maskRedo();},title:t('tools.redo')},'\u21AA');
      editBar.append(undoBtn,redoBtn);
      editBar.append(h('div',{style:{width:'1px',height:'1rem',background:'rgba(255,255,255,0.15)'}}));
      editBar.append(h('button',{style:{display:'inline-flex',alignItems:'center',gap:'0.3rem',fontSize:'0.72rem',color:'rgba(255,255,255,0.85)',
        background:'none',border:'none',cursor:'pointer',padding:'0.15rem 0.3rem',borderRadius:'3px',transition:'all .15s'},
        onClick:()=>{confirmMaskEdit();},
        onMouseover:function(){this.style.background='rgba(255,255,255,0.1)';},
        onMouseout:function(){this.style.background='none';}},
        h('kbd',{style:{background:'rgba(255,255,255,0.12)',border:'1px solid rgba(255,255,255,0.2)',borderRadius:'3px',padding:'0.1rem 0.35rem',fontSize:'0.6rem',fontFamily:'inherit',lineHeight:'1.1'}},'Enter'),
        ' '+t('clean.apply','apply')));
      editBar.append(h('button',{style:{display:'inline-flex',alignItems:'center',gap:'0.3rem',fontSize:'0.72rem',color:'rgba(255,255,255,0.5)',
        background:'none',border:'none',cursor:'pointer',padding:'0.15rem 0.3rem',borderRadius:'3px',transition:'all .15s'},
        onClick:()=>{cancelMaskEdit();},
        onMouseover:function(){this.style.background='rgba(255,255,255,0.1)';},
        onMouseout:function(){this.style.background='none';}},
        h('kbd',{style:{background:'rgba(255,255,255,0.08)',border:'1px solid rgba(255,255,255,0.15)',borderRadius:'3px',padding:'0.1rem 0.35rem',fontSize:'0.6rem',fontFamily:'inherit',lineHeight:'1.1'}},'Esc'),
        ' '+t('clean.cancel','cancel')));
      cv.append(editBar);
    }

    // Reset view - always present, shown/hidden dynamically
    const _isZoomed=S.viewScale!==1||S.viewX!==0||S.viewY!==0;
    cv.append(h('button',{id:'cleanResetBtn',style:{position:'absolute',top:'0.6rem',right:'5.1rem',zIndex:20,
      width:'2rem',height:'2rem',borderRadius:'50%',border:'1px solid rgba(255,255,255,0.12)',
      background:'rgba(15,15,20,0.75)',backdropFilter:'blur(20px)',WebkitBackdropFilter:'blur(20px)',
      color:'rgba(255,255,255,0.8)',fontSize:'1rem',cursor:'pointer',display:_isZoomed?'flex':'none',alignItems:'center',justifyContent:'center',
      boxShadow:'0 4px 12px rgba(0,0,0,0.4)',transition:'all .15s'},
      onClick:()=>{resetView();},title:t('tools.reset_zoom'),
      onMouseover:function(){this.style.background='rgba(15,15,20,0.9)';this.style.color='#fff';},
      onMouseout:function(){this.style.background='rgba(15,15,20,0.75)';this.style.color='rgba(255,255,255,0.8)';}},'\u27F2'));

    if(curFile()._cleanedUrl){
      cv.append(h('div',{className:'preview-popup'},h('div',{className:'preview-label'},t('clean.result')),h('img',{src:curFile()._cleanedUrl})));
    }
    ca.append(cv);
  } else if(curFile()){
    ca.append(h('div',{className:'empty-state'},
      h('div',{style:{fontSize:'0.85rem',fontWeight:'600',color:'var(--text)',marginBottom:'0.35rem'}},curFile().name),
      h('div',{className:'small',style:{marginBottom:'0.75rem'}},`${S.idx+1}/${S.allFiles.length}`),
      h('button',{className:'action-btn',style:{background:'rgba(110,170,255,0.12)',border:'1px solid rgba(110,170,255,0.2)'},
        onClick:()=>{S.cleanViewOpen=true;render();setTimeout(loadCurrentImage,30);}},t('tools.mask','Mask'))
    ));
  } else {
    ca.append(h('div',{className:'empty-state',style:{cursor:'pointer'},onClick:selectFolder},
      h('div',{style:{fontSize:'2.5rem',marginBottom:'0.5rem',opacity:0.3}},'\uD83D\uDCC1'),
      h('div',{className:'big'},t('source_modal.folder_desc')),
      h('div',{className:'small'},t('clean.click_here')),
    ));
  }

  // Batch progress panel
  if(showBatchLog){
    const pct=progressState.progress!=null?progressState.progress:(progressState.total>0?Math.round(progressState.current/progressState.total*100):0);
    const logEl=h('div',{className:'progress-log',id:'batchLog'});
    batchLog.forEach(line=>{const d=document.createElement('div');d.textContent=line;logEl.append(d);});
    const logHdr=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.6rem',marginTop:'0.5rem',marginBottom:'0.2rem'}});
    logHdr.append(h('span',{style:{fontSize:'0.6rem',fontWeight:'600',color:'var(--text3)',textTransform:'uppercase',letterSpacing:'0.6px'}},t('conv.log','Log')));
    const logBtns=h('div',{style:{display:'flex',gap:'0.3rem'}});
    const copyBtn=h('button',{style:{fontSize:'0.6rem',color:'var(--text3)',background:'none',border:'none',cursor:'pointer',padding:'0.1rem 0.3rem',borderRadius:'4px',transition:'color .15s'},
      onMouseover:function(){this.style.color='var(--text)';},
      onMouseout:function(){this.style.color='var(--text3)';},
      onClick:()=>{
        const el=document.getElementById('batchLog');
        if(!el)return;
        const text=[...el.children].map(d=>d.textContent).join('\n');
        navigator.clipboard.writeText(text).then(()=>{copyBtn.textContent='✓ '+t('ui.copied','Copied');setTimeout(()=>{copyBtn.textContent='⎘ '+t('ui.copy','Copy');},1500);});
      }},'⎘ '+t('ui.copy','Copy'));
    logBtns.append(copyBtn);
    if(!progressState.running){
      const clearBtn=h('button',{style:{fontSize:'0.6rem',color:'var(--text3)',background:'none',border:'none',cursor:'pointer',padding:'0.1rem 0.3rem',borderRadius:'4px',transition:'color .15s'},
        onMouseover:function(){this.style.color='var(--text)';},
        onMouseout:function(){this.style.color='var(--text3)';},
        onClick:()=>{progressState.log=[];progressState.phase='';progressState.currentFile='';render();}},'× '+t('ui.clear','Clear'));
      logBtns.append(clearBtn);
    }
    logHdr.append(logBtns);
    const panel=h('div',{className:'clean-batch-log'},
      h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.8rem'}},
        h('div',null,
          h('div',{className:'progress-text'},progressState.running?(autoActive?'✦ '+t('autonomous.processing','Autonomous processing...'):(progressState.phase==='detect'?'\uD83D\uDD0D '+t('clean.detecting','Detecting...'):'\uD83E\uDDF9 '+t('clean.cleaning','Cleaning...'))):t('conv.done','Done')),
          h('div',{className:'progress-sub',id:'batchInfo'},`${progressState.current} / ${progressState.total} \u2014 ${progressState.currentFile||''}`)
        ),
        logHdr
      ),
      h('div',{className:'progress-bar-o'},h('div',{className:'progress-bar-i',id:'batchBar',style:{width:pct+'%'}})),
      logEl
    );
    ca.append(panel);
    requestAnimationFrame(()=>{
      const el=$('batchLog');if(el)el.scrollTop=el.scrollHeight;
    });
  } else {
    S._batchLogScroll=undefined;S._batchLogUserScrolled=false;
  }

  main.append(ca);

  // Status bar
  const f=curFile();
  const devText=S.backend.device==='cuda'?('\u26A1 '+(S.backend.gpu||'GPU')):('\uD83D\uDDA5 '+(S.backend.cpu||'CPU'));
  main.append(h('div',{className:'status-bar'},
    h('span',null,f?`${S.idx+1}/${S.allFiles.length} \u00B7 ${f.name}`:t('clean.no_files')),
    h('span',{style:{color:S.processing?'var(--accent)':'var(--text3)'}},S.status||(S.processing?t('clean.processing'):t('conv.ready'))),
    h('span',null,devText)
  ));

  body.append(main);

  renderArtifactProfileOverlays(app);

  // Finetune popup
  if(S.showFinetunePopup){
    const popupBg=h('div',{style:{position:'fixed',inset:0,background:'rgba(0,0,0,0.6)',backdropFilter:'blur(8px)',zIndex:200,
      display:'flex',alignItems:'center',justifyContent:'center'}});
    const popup=h('div',{style:{background:'var(--glass3)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
      padding:'1.5rem',minWidth:'24rem',maxWidth:'28rem',boxShadow:'0 24px 64px rgba(0,0,0,0.5)',backdropFilter:'blur(40px)'}});
    popup.append(h('div',{style:{fontSize:'1.1rem',fontWeight:'600',marginBottom:'0.6rem'}},'\uD83D\uDCA1 '+t('train.finetune_popup_title')));
    popup.append(h('div',{style:{fontSize:'0.85rem',color:'var(--text2)',lineHeight:'1.5',marginBottom:'1rem'}},
      `${t('train.popup_detected_prefix','Detected')} ${S.finetuneCorrections} ${t('train.corrections_word','corrections')}. `+
      t('train.popup_detected_suffix','Fine-tune the model on this data? This will improve future detection accuracy.')));
    popup.append(h('div',{style:{fontSize:'0.75rem',color:'var(--text3)',marginBottom:'1rem'}},
      t('train.popup_saved_where','Corrections are saved in the corrections/ folder next to the app.')));

    let hideChecked=S.hideFinetunePopup;
    const checkRow=h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem',marginBottom:'1.2rem'}});
    const cb=h('input',{type:'checkbox',checked:hideChecked,onInput:e=>{
      hideChecked=e.target.checked;try{localStorage.setItem('mcs_hideFtPopup',hideChecked?'true':'false');}catch(ex){}
      S.hideFinetunePopup=hideChecked;}});
    checkRow.append(cb,h('span',{style:{fontSize:'0.8rem',color:'var(--text3)'}},t('train.dont_ask')));
    popup.append(checkRow);

    const btns=h('div',{style:{display:'flex',gap:'0.6rem',justifyContent:'flex-end'}});
    btns.append(h('button',{style:{padding:'0.5rem 1.2rem',borderRadius:'var(--radius-xs)',background:'var(--glass2)',
      color:'var(--text2)',border:'1px solid var(--glass-border)',fontSize:'0.85rem',fontWeight:'500'},
      onClick:()=>{S.showFinetunePopup=false;render();setTimeout(loadCurrentImage,30);}},t('train.later')));
    btns.append(h('button',{style:{padding:'0.5rem 1.2rem',borderRadius:'var(--radius-xs)',
      background:'linear-gradient(135deg,var(--accent),var(--accent2))',color:'#fff',border:'none',fontSize:'0.85rem',fontWeight:'600'},
      onClick:()=>{S.showFinetunePopup=false;S.tab='train';startFinetune();render();}},t('train.finetune')));
    popup.append(btns);
    popupBg.append(popup);
    app.append(popupBg);
  }

  app.append(body);
}

function renderTrain(app){
  const ts=S.trainStatus;
  if(!S.trainMode)S.trainMode='pairs';

  function numInput(value,onCommit,min,max){
    const wrap=h('div',{style:{display:'flex',alignItems:'center',gap:'0.3rem'}});
    const bst={width:'1.6rem',height:'1.6rem',display:'flex',alignItems:'center',justifyContent:'center',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'8px',color:'var(--text2)',
      cursor:'pointer',fontSize:'0.85rem',fontWeight:'500',transition:'all .15s',padding:0,lineHeight:1};
    const inp=h('input',{type:'text',inputMode:'numeric',value:String(value),
      style:{width:'3.5rem',background:'var(--glass)',border:'1px solid var(--glass-border)',borderRadius:'8px',
        padding:'0.3rem 0.2rem',fontSize:'0.78rem',color:'var(--accent)',fontFamily:'var(--font-mono)',fontWeight:'700',
        outline:'none',textAlign:'center',transition:'border-color .2s'},
      onFocus:function(){this.style.borderColor='var(--accent)';},
      onBlur:function(){this.style.borderColor='var(--glass-border)';let v=parseInt(this.value)||min;v=Math.max(min,Math.min(max,v));this.value=v;onCommit(v,true);},
      onInput:e=>{let v=parseInt(e.target.value);if(!isNaN(v)){v=Math.max(min,Math.min(max,v));onCommit(v,true);}},
      onKeydown:e=>{if(e.key==='Enter')e.target.blur();}});
    wrap.append(h('button',{style:{...bst},onClick:()=>{const v=Math.max(min,value-1);onCommit(v);render();},
      onMouseover:function(){this.style.borderColor='var(--accent)';this.style.color='var(--accent)';},
      onMouseout:function(){this.style.borderColor='var(--glass-border)';this.style.color='var(--text2)';}},'-'));
    wrap.append(inp);
    wrap.append(h('button',{style:{...bst},onClick:()=>{const v=Math.min(max,value+1);onCommit(v);render();},
      onMouseover:function(){this.style.borderColor='var(--accent)';this.style.color='var(--accent)';},
      onMouseout:function(){this.style.borderColor='var(--glass-border)';this.style.color='var(--text2)';}},'+'));
    return wrap;
  }

  const body=h('div',{className:'body'});

  // Encoding-normalized comment.
  const sb=h('div',{className:'sidebar'});
  const sbh=h('div',{className:'sidebar-hdr'});
  const titleRow=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between'}});
  const titleLeft=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem'}});
  titleLeft.append(h('span',{style:{fontSize:'0.82rem',fontWeight:'600',color:'var(--text)'}},t('train.title','Training')));
  titleRow.append(titleLeft);
  const titleBtns=h('div',{style:{display:'flex',gap:'0.3rem'}});
  if(S.backend.modelLoaded){
    titleBtns.append(h('div',{style:{background:'rgba(52,211,153,0.1)',border:'1px solid rgba(52,211,153,0.2)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--green)',fontSize:'0.65rem'},
      title:'Model loaded'},'\u25CF'));
  } else {
    titleBtns.append(h('button',{style:{background:'rgba(251,146,60,0.1)',border:'1px solid rgba(251,146,60,0.2)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',
      color:'var(--orange)',fontSize:'0.7rem',transition:'all .2s'},
      onClick:loadModelFile,title:'Load Model',
      onMouseover:function(){this.style.background='rgba(251,146,60,0.2)';this.style.borderColor='rgba(251,146,60,0.4)';},
      onMouseout:function(){this.style.background='rgba(251,146,60,0.1)';this.style.borderColor='rgba(251,146,60,0.2)';}},'\u2191'));
  }
  titleRow.append(titleBtns);
  sbh.append(titleRow);
  sb.append(sbh);

  // Mode selector
  const modes=[
    {key:'pairs',icon:'\uD83C\uDF93',label:t('train.title_pairs','Training on pairs'),desc:t('train.desc_pairs','Original + cleaned')},
    {key:'finetune',icon:'\u26A1',label:t('train.title_finetune','Finetune'),desc:t('train.desc_finetune','On corrections')}
  ];
  const modeList=h('div',{style:{padding:'0.4rem'}});
  modes.forEach(m=>{
    const active=S.trainMode===m.key;
    const item=h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem',padding:'0.5rem 0.6rem',
      borderRadius:'var(--radius-xs)',cursor:'pointer',transition:'all .15s',marginBottom:'0.2rem',
      background:active?'var(--glass3)':'none',border:active?'1px solid var(--glass-border2)':'1px solid transparent'},
      onClick:()=>{S.trainMode=m.key;render();},
      onMouseover:function(){if(!active)this.style.background='var(--glass2)';},
      onMouseout:function(){if(!active)this.style.background='none';}});
    item.append(h('span',{style:{fontSize:'1rem'}},m.icon));
    const info=h('div',{style:{flex:'1',overflow:'hidden'}});
    info.append(h('div',{style:{fontSize:'0.78rem',fontWeight:active?'600':'400',color:active?'var(--text)':'var(--text2)'}},m.label));
    info.append(h('div',{style:{fontSize:'0.62rem',color:'var(--text3)'}},m.desc));
    item.append(info);
    if(m.key==='finetune'){
      const corr=ts.corrections_count||0;
      item.append(h('span',{style:{fontSize:'0.65rem',fontWeight:'600',padding:'0.15rem 0.45rem',borderRadius:'10px',
        background:corr>0?'rgba(52,211,153,0.1)':'var(--glass2)',color:corr>0?'var(--green)':'var(--text3)',
        border:'1px solid '+(corr>0?'rgba(52,211,153,0.2)':'var(--glass-border)')}},String(corr)));
    }
    modeList.append(item);
  });
  sb.append(modeList);

  // Device info
  const devText=S.backend.device==='cuda'?`\u26A1 GPU: ${S.backend.gpu||'CUDA'}`:`\uD83D\uDDA5 CPU: ${S.backend.cpu||'CPU'}`;
  sb.append(h('div',{style:{padding:'0.5rem 0.8rem',fontSize:'0.65rem',color:'var(--text3)',borderTop:'1px solid var(--glass-border)',marginTop:'auto'}},devText));

  // Sidebar footer: start button
  const sbFooter=h('div',{style:{padding:'0.5rem',borderTop:'1px solid var(--glass-border)',flexShrink:0}});
  if(!ts.training){
    const isPairs=S.trainMode==='pairs';
    const canStart=isPairs?(S.trainOrigDir&&S.trainCleanDir):((ts.corrections_count||0)>0||S.finetuneDir);
    const startFn=isPairs?startTraining:startFinetune;
    const goBtn=h('button',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      width:'100%',padding:'0.55rem',borderRadius:'var(--radius-xs)',fontSize:'0.78rem',fontWeight:'600',
      cursor:'pointer',transition:'all .2s',border:'none',color:'#fff',
      background:isPairs?'linear-gradient(135deg,var(--accent),var(--accent2))':'linear-gradient(135deg,var(--accent2),var(--accent))',
      opacity:canStart?'1':'0.35'},
      onClick:()=>{if(canStart)startFn();}});
    goBtn.append(isPairs?'\ud83d\ude80':'\u26a1');
    goBtn.append(t('train.start','Start training'));
    sbFooter.append(goBtn);
  } else {
    const stopBtn=h('button',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      width:'100%',padding:'0.55rem',borderRadius:'var(--radius-xs)',fontSize:'0.78rem',fontWeight:'600',
      cursor:'pointer',transition:'all .2s',
      background:'var(--red-bg)',border:'1px solid rgba(248,113,113,0.2)',color:'var(--red)'},
      onClick:()=>apiPost('/api/train/stop',{})});
    stopBtn.append('\u23F9');
    stopBtn.append((ts.progress||0)+'% \u2014 '+t('train.stop','Stop'));
    sbFooter.append(stopBtn);
  }
  sb.append(sbFooter);
  body.append(sb);

  // Encoding-normalized comment.
  const main=h('div',{className:'main'});

  // Toolbar
  const tb=h('div',{className:'toolbar'});
  if(ts.training){
    tb.append(h('span',{style:{fontSize:'0.78rem',color:'var(--text)'}},`${t('train.epoch','Epoch')} ${ts.epoch_current||0} / ${ts.epochs_total||0}`));
    tb.append(h('span',{style:{fontSize:'0.78rem',color:'var(--accent)',fontWeight:'600',marginLeft:'0.5rem'}},ts.progress+'%'));
  }
  main.append(tb);

  // Encoding-normalized comment.
  const ca=h('div',{className:'canvas-area',style:{alignItems:'flex-start',justifyContent:'flex-start',overflow:'auto'}});
  const settings=h('div',{className:'conv-settings'});

  if(S.trainMode==='pairs'){
    // Encoding-normalized comment.
    const titleRow=h('div',{style:{marginBottom:'0.8rem'}});
    titleRow.append(h('div',{style:{fontSize:'1.2rem',fontWeight:'700',color:'var(--text)',letterSpacing:'-0.02em'}},'\uD83C\uDF93 '+t('train.title_pairs')));
    titleRow.append(h('div',{style:{fontSize:'0.72rem',color:'var(--text3)',marginTop:'2px'}},t('train.desc_pairs')));
    settings.append(titleRow);

    const mkRow=(label,value,key)=>{
      return h('div',{className:'train-path-row'},
        h('span',{className:'train-path-label'},label),
        h('div',{className:'train-path-value',style:{color:value?'var(--accent)':'var(--text3)'},
          title:value||t('train.select_folder'),onClick:()=>browseFolder(key)},
          value?value.split(/[/\\]/).slice(-2).join('/'):t('train.not_selected')));
    };
    settings.append(mkRow(t('clean.before'),S.trainOrigDir,'trainOrigDir'));
    settings.append(mkRow(t('clean.after'),S.trainCleanDir,'trainCleanDir'));
    settings.append(h('div',{className:'train-path-row'},
      h('span',{className:'train-path-label'},t('train.model_label')),
      h('div',{className:'train-path-value',style:{color:'var(--accent)'},title:S.trainBaseModel+'\n'+t('train.select_model_file','Click to choose .pt file'),
        onClick:browseModelFile},S.trainBaseModel)));
    settings.append(h('div',{style:{fontSize:'0.62rem',color:'var(--text3)',padding:'0 0.2rem',marginBottom:'0.6rem'}},
      t('train.model_usage_note','yolov8n-seg.pt = from scratch \u00B7 custom .pt = fine-tuning')));

    const pRow=h('div',{style:{display:'flex',alignItems:'center',gap:'1rem',flexWrap:'wrap'}});
    pRow.append(h('div',{className:'train-param'},h('span',{className:'train-param-label'},t('train.epochs')),numInput(S.trainEpochs,v=>{S.trainEpochs=v;},1,9999)));
    pRow.append(h('div',{className:'train-param'},h('span',{className:'train-param-label'},t('tools.size')),numInput(S.trainImgSize,v=>{S.trainImgSize=v;},128,9999)));
    settings.append(pRow);

  } else {
    // Encoding-normalized comment.
    const corr=ts.corrections_count||0;
    const titleRow=h('div',{style:{marginBottom:'0.8rem'}});
    titleRow.append(h('div',{style:{fontSize:'1.2rem',fontWeight:'700',color:'var(--text)',letterSpacing:'-0.02em'}},'\u26A1 '+t('train.title_finetune')));
    titleRow.append(h('div',{style:{fontSize:'0.72rem',color:'var(--text3)',marginTop:'2px'}},
      t('train.desc_finetune')+' \u00B7 '+corr+' '+t('train.corrections_word','corrections')));
    settings.append(titleRow);

    const corrDir=S.finetuneDir||ts.corrections_dir||'';
    settings.append(h('div',{className:'train-path-row'},
      h('span',{className:'train-path-label'},t('train.images_dir')),
      h('div',{className:'train-path-value',style:{color:corrDir?'var(--accent)':'var(--text3)'},
        title:corrDir||t('train.corrections_dir'),
        onClick:()=>browseFolder('finetuneDir')},corrDir?corrDir.split(/[/\\]/).slice(-2).join('/'):t('train.auto'))));

    const ftModel=S.finetuneModel||t('train.current_model');
    settings.append(h('div',{className:'train-path-row'},
      h('span',{className:'train-path-label'},t('train.model_label')),
      h('div',{className:'train-path-value',style:{color:S.finetuneModel?'var(--accent)':'var(--text3)'},
        title:S.finetuneModel||t('train.uses_current'),
        onClick:async()=>{try{const r=await(await apiPost('/api/browse-file',{filetypes:[["YOLO Model","*.pt"]]})).json();if(r.path){S.finetuneModel=r.path;render();}}catch(e){}}},
        ftModel.split(/[/\\]/).pop())));
    settings.append(h('div',{style:{fontSize:'0.6rem',color:'var(--text3)',padding:'0 0.2rem',marginBottom:'0.6rem'}},
      'corrections/original/ + corrections/masks/'));

    const pRow=h('div',{style:{display:'flex',alignItems:'center',gap:'1rem',flexWrap:'wrap'}});
    pRow.append(h('div',{className:'train-param'},h('span',{className:'train-param-label'},t('train.epochs')),numInput(S.finetuneEpochs,v=>{S.finetuneEpochs=v;},1,9999)));
    pRow.append(h('div',{className:'train-param'},h('span',{className:'train-param-label'},t('tools.size')),numInput(S.finetuneImgSize,v=>{S.finetuneImgSize=v;},128,9999)));
    settings.append(pRow);
  }

  // Encoding-normalized comment.
  if(ts.training||ts.progress>0){
    settings.append(h('div',{style:{height:'1px',background:'var(--glass-border)',margin:'1rem 0'}}));
    const progWrap=h('div',{});
    progWrap.append(h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.4rem'}},
      h('span',{id:'trainInfo',style:{fontSize:'0.85rem',fontWeight:'500',color:'var(--text)'}},ts.training?`${t('train.epoch','Epoch')} ${ts.epoch_current} / ${ts.epochs_total}`:'\u2705 '+t('train.done','Done')),
      h('span',{style:{fontSize:'0.85rem',color:'var(--accent)',fontWeight:'600'}},ts.progress+'%')));
    progWrap.append(h('div',{className:'t-progress-bar-o'},h('div',{className:'t-progress-bar-i',id:'trainBar',style:{width:ts.progress+'%'}})));
    settings.append(progWrap);
  }

  // Encoding-normalized comment.
  if(ts.log&&ts.log.length>0){
    settings.append(h('div',{style:{height:'1px',background:'var(--glass-border)',margin:'1rem 0'}}));
    settings.append(h('div',{style:{fontSize:'0.65rem',fontWeight:'600',color:'var(--text3)',textTransform:'uppercase',
      letterSpacing:'1px',marginBottom:'0.4rem'}},t('conv.log')));
    const trainLogDiv=h('div',{className:'train-log',id:'trainLog'});
    ts.log.forEach(line=>{const d=document.createElement('div');d.textContent=line;trainLogDiv.append(d);});
    settings.append(trainLogDiv);
  }

  ca.append(settings);
  main.append(ca);

  // Status bar
  const statusText=ts.training?`Epoch ${ts.epoch_current||0}/${ts.epochs_total||0} \u2014 ${ts.progress||0}%`:t('conv.ready');
  main.append(h('div',{className:'status-bar'},
    h('span',null,S.trainMode==='pairs'?t('train.title_pairs'):t('train.title_finetune')),
    h('span',{style:{color:ts.training?'var(--accent)':'var(--text3)'}},statusText)));

  body.append(main);
  app.append(body);
}



// Encoding-normalized comment.
async function loadConvertProfiles(force=false){
  if(S.convProfiles&&!force)return;
  try{
    const d=await apiGet('/api/convert/profiles');
    S.convProfiles=d.profiles;
    S.convMobiAvailable=d.mobi_available;
    S.convMobiTool=d.mobi_tool;
    S.convMobiPath=d.mobi_path||'';
    S.conv7zAvailable=d.sevenzip_available!==false;
    S.convPreviewerAvailable=d.previewer_available!==false;
    S.convKfxAvailable=d.kfx_cli_available===true;
    render();
  }catch(e){console.error(e);}
}
async function pollConvertStatus(){
  if(S.convPollInFlight)return;
  S.convPollInFlight=true;
  try{
    const st=await apiGet('/api/convert/status');
    const wasConverting=S.convStatus.converting;
    S.convStatus=st;
    if(typeof st.advanced_log==='boolean'){
      S.convAdvancedLog=st.advanced_log;
      localStorage.setItem('mcs_convAdvancedLog', S.convAdvancedLog?'true':'false');
    }
    if(!st.converting){
      if(S.convPollId){clearTimeout(S.convPollId);S.convPollId=null;}
      S.convPollInFlight=false;
      render();
      return;
    }
    if(!wasConverting){render();}else{_patchConvertUI();}
  }catch(e){}
  finally{S.convPollInFlight=false;}
  _scheduleConvertPoll();
}
function _getConvertPollDelay(){
  const st=S.convStatus||{};
  if(document.hidden)return 10000;
  if(st.converting){
    // Faster at active progress, slower near completion.
    return (st.progress||0)>=95?2000:1200;
  }
  return 4000;
}
function _scheduleConvertPoll(delay){
  if(S.convPollId){clearTimeout(S.convPollId);S.convPollId=null;}
  const next=typeof delay==='number'?delay:_getConvertPollDelay();
  S.convPollId=setTimeout(pollConvertStatus,next);
}
function _convStatusDetail(status){
  return status.current_file?(status.phase?status.phase+' \u00B7 ':'')+status.current_file:(status.phase||'');
}
function _convStatusPresentation(status){
  if(status.converting)return {label:t('conv.converting','Converting...'),color:'var(--accent)',icon:'\u23f3',done:false};
  const phase=String(status.phase||'').trim().toLowerCase();
  if(phase==='error')return {label:t('conv.failed','Failed'),color:'var(--red)',icon:'\u26a0',done:false};
  if(phase==='stopped')return {label:t('conv.stopped','Stopped'),color:'var(--text3)',icon:'\u23f9',done:false};
  if(phase==='done!'||phase==='done'||status.output_files&&status.output_files.length){
    return {label:t('conv.done','Done'),color:'var(--green)',icon:'\u2705',done:true};
  }
  return {label:t('conv.ready'),color:'var(--text3)',icon:'\u23f3',done:false};
}
function _convFooterState(){
  const status=S.convStatus||{};
  const sources=S.convSources||[];
  const files=sources.flatMap(source=>(S.convScanned||{})[source]||[]);
  const loading=sources.filter(source=>!Array.isArray((S.convScanned||{})[source])).length;
  // Count affected input files, including equal relative names in two volumes.
  const noCrop=files.filter(file=>(S.convExclusions||{})[file.relPath]?.['no-crop']).length;
  const customCrop=files.filter(file=>(S.convCustomCrop||{})[file.relPath]).length;
  const excluded=files.filter(file=>(S.convExcluded||{})[file.relPath]).length;
  const scanned=sources.includes(S.convExpandedSource)?(S.convScanned||{})[S.convExpandedSource]:null;
  const viewed=scanned&&S.convViewIdx!==null&&S.convViewIdx>=0?scanned[S.convViewIdx]:null;
  let left=t('conv.no_sources');
  if(viewed){
    left=t('conv.preview_file_counter','Preview {current}/{total}')
      .replace('{current}',String(S.convViewIdx+1)).replace('{total}',String(scanned.length))+' \u00B7 '+viewed.name;
  }else if(sources.length){
    left=excluded?(files.length-excluded)+' / '+files.length+' '+t('conv.files_included','files included')+' \u00B7 '+sources.length+' '+t('conv.sources_word','sources'):
      files.length+' '+t('conv.files_in_sources','files in')+' '+sources.length+' '+t('conv.sources_word','sources');
  }
  if(loading)left+=' \u00B7 '+t('conv.loading_sources','Loading: {count}').replace('{count}',String(loading));
  const presentation=_convStatusPresentation(status);
  const middle=status.converting?(_convStatusDetail(status)||presentation.label):presentation.label;
  const parts=[];
  if(noCrop)parts.push('No crop: '+noCrop);
  if(customCrop)parts.push('Custom crop: '+customCrop);
  if(excluded)parts.push('Excluded: '+excluded);
  let profile=null;
  if(S.convProfiles)Object.values(S.convProfiles).forEach(group=>{if(group[S.convProfile])profile=group[S.convProfile];});
  if(profile)parts.push(profile.name+' \u00B7 '+S.convFormat);
  return {left,middle,right:parts.length?t('conv.current_settings','Settings')+': '+parts.join(' \u00B7 '):'',color:presentation.color};
}
function _convRenderStatusBar(){
  const footer=_convFooterState();
  const textStyle={minWidth:0,overflowWrap:'anywhere'};
  return h('div',{className:'status-bar',style:{flexWrap:'wrap',gap:'0.2rem 0.8rem'}},
    h('span',{id:'convFooterFiles',title:footer.left,style:{...textStyle,flex:'1 1 14rem'}},footer.left),
    h('span',{id:'convFooterStatus',title:footer.middle,style:{...textStyle,color:footer.color,flex:'1 1 18rem'}},footer.middle),
    h('span',{id:'convFooterRules',title:footer.right,style:{...textStyle,flex:'1 1 14rem',textAlign:'right'}},footer.right));
}
function _convPatchStatusBar(){
  const footer=_convFooterState();
  [['convFooterFiles',footer.left],['convFooterStatus',footer.middle],['convFooterRules',footer.right]].forEach(([id,text])=>{
    const element=document.getElementById(id);
    if(element){element.textContent=text;element.title=text;}
  });
  const status=document.getElementById('convFooterStatus');
  if(status)status.style.color=footer.color;
}
function _patchConvertUI(){
  const st=S.convStatus;
  const pct=(st.progress||0)+'%';

  // Encoding-normalized comment.
  const tbFill=document.getElementById('tbProgressFill');
  if(tbFill)tbFill.style.width=pct;
  const tbPct=document.getElementById('tbProgressPct');
  if(tbPct)tbPct.textContent=pct;
  const tbPhase=document.getElementById('tbProgressPhase');
  if(tbPhase)tbPhase.textContent=st.phase||t('conv.converting','Converting...');

  // Encoding-normalized comment.
  const bar=document.getElementById('convBar');
  if(bar)bar.style.width=pct;

  // Encoding-normalized comment.
  const pct2=document.getElementById('tbProgressPct2');
  if(pct2)pct2.textContent=st.converting?pct:'';

  // Encoding-normalized comment.
  const info=document.getElementById('convInfo');
  if(info)info.textContent=_convStatusDetail(st);
  _convPatchStatusBar();

  // Encoding-normalized comment.
  const logEl=document.getElementById('convLog');
  if(logEl&&st.log){
    const existing=logEl.children.length;
    if(existing>0&&existing===st.log.length){
      // Same length — check if last line changed (in-place progress update).
      const last=logEl.lastElementChild;
      if(last&&last.textContent!==st.log[st.log.length-1]){
        last.textContent=st.log[st.log.length-1];
      }
    } else {
      for(let i=existing;i<st.log.length;i++){
        const line=document.createElement('div');line.textContent=st.log[i];logEl.append(line);
      }
    }
    logEl.scrollTop=logEl.scrollHeight;
  }
}
async function showComicInfoModal(source, scannedFiles, mode='meta') {
  const isTocMode = mode === 'toc';
  // Fetch current ComicInfo.xml (if exists)
  let existing = {};
  let xmlExists = false;
  try {
    const r = await (await apiPost('/api/comicinfo/read', {source})).json();
    if (r.ok) {
      existing = r.fields || {};
      existing._bookmarks = r.bookmarks || [];
      existing._anchorBookmarks = r.bookmarkAnchors || [];
      xmlExists = r.exists;
      // Encoding-normalized comment.
      if (existing._bookmarks.length > 0 && scannedFiles) {
        existing._bookmarks.forEach(([pageIdx, name]) => {
          if (scannedFiles[pageIdx] && name && !S.convBookmarks[scannedFiles[pageIdx].relPath]) {
            const rp = scannedFiles[pageIdx].relPath;
            const prevOrigin = _convBookmarkOriginOf(rp);
            _convSetBookmarkWithOrigin(rp, name, source, prevOrigin === 'auto' ? 'auto' : 'manual');
          }
        });
        render();
      }
    }
  } catch(e) {}

  // ComicInfo fields definition: [key, label, type, options?]
  const FIELDS_BASIC = [
    ['Title',         'Title',          'text'],
    ['Series',        'Series',         'text'],
    ['Number',        'Number',         'text'],
    ['Volume',        'Volume',         'number'],
    ['Writer',        'Writer',         'text'],
    ['Translator',    'Translator',     'text'],
    ['LanguageISO',   'Language (ISO)', 'text'],
    ['Year',          'Year',           'number'],
    ['Manga',         'Manga',          'select', ['Yes','YesAndRightToLeft','No']],
    ['AgeRating',     'Age Rating',     'select', ['Unknown','All ages','G','PG','PG-13','M','MA15+','R18+','X18+','Adults Only 18+','Early Childhood','Everyone','Everyone 10+','Kids to Adults','Teen','Rating Pending']],
  ];
  const FIELDS_ADVANCED = [
    ['Summary',       'Summary',        'textarea'],
    ['Publisher',     'Publisher',      'text'],
    ['Genre',         'Genre',          'text'],
    ['Count',         'Count',          'number'],
    ['Month',         'Month',          'number'],
    ['Penciller',     'Penciller',      'text'],
    ['Inker',         'Inker',          'text'],
    ['Colorist',      'Colorist',       'text'],
    ['Letterer',      'Letterer',       'text'],
    ['CoverArtist',   'Cover Artist',   'text'],
    ['Tags',          'Tags',           'text'],
    ['BlackAndWhite', 'Black & White',  'select', ['Yes','No']],
    ['ScanInformation','Scan Info',     'text'],
    ['Web',           'Web URL',        'text'],
  ];
  const FIELDS = [...FIELDS_BASIC, ...FIELDS_ADVANCED];

  const srcName = source.split(/[/\\]/).filter(Boolean).slice(-1)[0];

  // Build overlay + modal
  const overlay = document.createElement('div');
  Object.assign(overlay.style, {position:'fixed',inset:'0',background:'rgba(0,0,0,0.6)',
    backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',zIndex:'10000',
    display:'flex',alignItems:'center',justifyContent:'center'});
  overlay.onclick = e => { if(e.target===overlay) close(); };

  const modal = document.createElement('div');
  Object.assign(modal.style, {background:'var(--bg2)',border:'1px solid var(--glass-border2)',
    borderRadius:'var(--radius)',padding:'1.25rem 1.5rem',width:'min(560px,92vw)',maxHeight:'85vh',
    boxShadow:'0 24px 80px rgba(0,0,0,0.55)',display:'flex',flexDirection:'column',gap:'0.75rem',overflow:'hidden'});

  // Header
  const hdr = document.createElement('div');
  Object.assign(hdr.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem'});
  const hdrLeft = document.createElement('div');
  hdrLeft.innerHTML = `<div style="font-size:0.85rem;font-weight:600;color:var(--text)">${isTocMode?'TOC / Chapters':'ComicInfo.xml'}</div>
    <div style="font-size:0.62rem;color:var(--text3);margin-top:1px">${srcName}${xmlExists?' \u00B7 editing existing':' \u00B7 will be created'}</div>`;
  const closeBtn = document.createElement('button');
  Object.assign(closeBtn.style, {background:'none',border:'none',color:'var(--text3)',cursor:'pointer',
    fontSize:'1.1rem',lineHeight:'1',padding:'0.1rem 0.2rem',transition:'color .2s'});
  closeBtn.innerHTML = '\u2715'; closeBtn.onmouseenter=()=>{closeBtn.style.color='var(--text)';}; closeBtn.onmouseleave=()=>{closeBtn.style.color='var(--text3)';};
  closeBtn.onclick = close;
  hdr.append(hdrLeft, closeBtn);
  modal.append(hdr);

  // Divider
  const div0 = document.createElement('div');
  Object.assign(div0.style, {
    height:'1px',
    background:isTocMode ? 'rgba(255,255,255,0.12)' : 'var(--glass-border)',
    margin:'0 -1.5rem'
  });
  modal.append(div0);

  const vals = {};
  const inputs = {};

  const baseStyle = {width:'100%',background:'var(--glass2)',border:'1px solid var(--glass-border)',
    borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.72rem',fontFamily:'inherit',
    outline:'none',transition:'border-color .15s',boxSizing:'border-box'};

  const mkField = (grid, [key, label, type, opts]) => {
    const wrap = document.createElement('div');
    if (type === 'textarea' || key === 'Summary') wrap.style.gridColumn = '1 / -1';
    const lbl = document.createElement('div');
    Object.assign(lbl.style, {fontSize:'0.58rem',fontWeight:'600',textTransform:'uppercase',
      letterSpacing:'0.8px',color:'var(--text3)',marginBottom:'0.25rem'});
    lbl.textContent = label;
    wrap.append(lbl);

    let inp;
    if (type === 'textarea') {
      inp = document.createElement('textarea');
      Object.assign(inp.style, {...baseStyle, padding:'0.35rem 0.5rem', resize:'vertical', minHeight:'3.5rem'});
      inp.value = existing[key] || '';
      vals[key] = inp.value;
      inp.addEventListener('input', () => { vals[key] = inp.value; });
      inp.onfocus = () => { inp.style.borderColor='var(--accent)'; };
      inp.onblur  = () => { inp.style.borderColor='var(--glass-border)'; };
      inputs[key] = inp;
      wrap.append(inp);
    } else if (type === 'select') {
      vals[key] = existing[key] || '';
      const ddOpts = ['', ...opts].map(o => ({value:o, label:o||'\u2014'}));
      const dd = mkCustomSelect(ddOpts, {value:vals[key], style:{width:'100%'},
        onChange: v => { vals[key] = v; }});
      inputs[key] = dd;
      wrap.append(dd);
    } else if (type === 'number') {
      inp = document.createElement('input');
      inp.type = 'text';
      inp.inputMode = 'numeric';
      inp.value = existing[key] || '';
      vals[key] = inp.value;
      const numRow = document.createElement('div');
      Object.assign(numRow.style, {display:'flex',gap:'0',alignItems:'stretch'});
      const btnSt = {display:'flex',alignItems:'center',justifyContent:'center',
        background:'var(--glass2)',border:'1px solid var(--glass-border)',color:'var(--text2)',
        cursor:'pointer',fontSize:'0.8rem',fontWeight:'600',transition:'all .15s',padding:'0 0.45rem',
        lineHeight:'1',userSelect:'none',flexShrink:'0'};
      const mkBtn = (text, delta, radius) => {
        const b = document.createElement('button');
        Object.assign(b.style, {...btnSt, borderRadius:radius});
        b.textContent = text;
        b.onmouseenter = () => { b.style.borderColor='var(--accent)'; b.style.color='var(--accent)'; };
        b.onmouseleave = () => { b.style.borderColor='var(--glass-border)'; b.style.color='var(--text2)'; };
        b.onclick = () => { let v = (parseInt(inp.value) || 0) + delta; if(v<0)v=0; inp.value=v; vals[key]=String(v); };
        return b;
      };
      Object.assign(inp.style, {...baseStyle, padding:'0.3rem 0.3rem', textAlign:'center',
        borderRadius:'0', borderLeft:'none', borderRight:'none', flex:'1 1 auto', minWidth:'0',
        marginLeft:'-1px', marginRight:'-1px', position:'relative'});
      inp.addEventListener('input', () => { vals[key] = inp.value; });
      inp.onfocus = () => { inp.style.borderLeft='1px solid var(--accent)'; inp.style.borderRight='1px solid var(--accent)'; inp.style.borderColor='var(--accent)'; inp.style.zIndex='1'; };
      inp.onblur  = () => { inp.style.borderLeft='none'; inp.style.borderRight='none'; inp.style.borderColor='var(--glass-border)'; inp.style.zIndex='0'; };
      inputs[key] = inp;
      if (key === 'Volume') {
        const _vpDefault = t('conv.vol_prefix','Vol.');
        const _vpCur = S.convVolPrefix || _vpDefault;
        const _vpOpts = [_vpCur, ..._volPrefixes.filter(v => v !== _vpCur)];
        const vpSel = mkCustomSelect(_vpOpts.map(v=>({value:v,label:v})),
          {value:_vpCur, style:{
            minWidth:'4rem',flex:'0 0 auto',borderRadius:'var(--radius-xs)',
            fontSize:'0.72rem',height:'auto'},
          onChange:v=>{S.convVolPrefix=v;localStorage.setItem('mcs_convVolPrefix',v);}});
        numRow.append(vpSel);
        const spacer = document.createElement('div');
        spacer.style.width = '0.35rem';
        spacer.style.flexShrink = '0';
        numRow.append(spacer);
      }
      numRow.append(mkBtn('\u2212', -1, 'var(--radius-xs) 0 0 var(--radius-xs)'));
      numRow.append(inp);
      numRow.append(mkBtn('+', 1, '0 var(--radius-xs) var(--radius-xs) 0'));
      wrap.append(numRow);
    } else {
      inp = document.createElement('input');
      inp.type = 'text';
      Object.assign(inp.style, {...baseStyle, padding:'0.3rem 0.5rem'});
      inp.value = existing[key] || '';
      vals[key] = inp.value;
      inp.addEventListener('input', () => { vals[key] = inp.value; });
      inp.onfocus = () => { inp.style.borderColor='var(--accent)'; };
      inp.onblur  = () => { inp.style.borderColor='var(--glass-border)'; };
      inputs[key] = inp;
      wrap.append(inp);
    }
    grid.append(wrap);
  };

  if (!isTocMode) {
    // Encoding-normalized comment.
    const bodyWrap = document.createElement('div');
    Object.assign(bodyWrap.style, {overflow:'hidden auto',margin:'0 -1.5rem',padding:'0 1.5rem',flex:'1',minHeight:0});
    const body = document.createElement('div');
    Object.assign(body.style, {display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.55rem 0.9rem',paddingBottom:'0.25rem'});

    // Basic fields
    FIELDS_BASIC.forEach(f => mkField(body, f));

  // Advanced section - collapsible
  let advOpen = FIELDS_ADVANCED.some(([key]) => existing[key] && existing[key].trim());
  const advGrid = document.createElement('div');
  Object.assign(advGrid.style, {display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.55rem 0.9rem',
    gridColumn:'1 / -1', marginTop:'0.1rem'});
  FIELDS_ADVANCED.forEach(f => mkField(advGrid, f));

  const advToggle = document.createElement('div');
  advToggle.style.gridColumn = '1 / -1';
  Object.assign(advToggle.style, {display:'flex',alignItems:'center',gap:'0.5rem',
    cursor:'pointer',userSelect:'none',padding:'0.3rem 0',marginTop:'0.2rem'});
  const advLine = () => { const l=document.createElement('div'); Object.assign(l.style,{flex:'1',height:'1px',background:'var(--glass-border)'}); return l; };
  const advArrow = document.createElement('span');
  Object.assign(advArrow.style, {fontSize:'0.55rem',color:'var(--text3)',transition:'transform .2s'});
  const advLabel = document.createElement('span');
  Object.assign(advLabel.style, {fontSize:'0.6rem',fontWeight:'600',textTransform:'uppercase',
    letterSpacing:'0.8px',color:'var(--text3)',whiteSpace:'nowrap'});

  const updateAdv = () => {
    advGrid.style.display = advOpen ? 'grid' : 'none';
    advArrow.textContent = advOpen ? '\u25B2' : '\u25BE';
    advLabel.textContent = advOpen ? t('toc.hide_advanced','Hide advanced') : t('toc.show_advanced','Advanced fields');
  };
  updateAdv();
  advToggle.onclick = () => { advOpen = !advOpen; updateAdv(); };
  advToggle.append(advLine(), advArrow, advLabel, advLine());

  const advWrap = document.createElement('div');
  advWrap.style.gridColumn = '1 / -1';
  advWrap.append(advToggle, advGrid);
    body.append(advWrap);

    bodyWrap.append(body);
    modal.append(bodyWrap);
  }

  // Encoding-normalized comment.
  let chapterMap = {};
  let flatBookmarks = []; // [{idx, relPath, name}]
  let folderExtraBookmarks = []; // [{idx, relPath, name}]
  let hasFolders = false;
  let isFlat = false;
  let applyFolderNames = null;
  let canRevertFolderNames = false;
  let restoreFolderNames = null;
  let getCopyFoldersLabel = () => 'Copy folder names';
  let refreshCopyFolderBtn = null;
  let toggleTocSeparator = null;
  let getTocSeparatorLabel = () => t('toc.separator_to_colon', 'Use : separator');
  let refreshTocSeparatorBtn = null;
  let openChapterSearch = null;
  if (isTocMode) {

  // Encoding-normalized comment.
  // Encoding-normalized comment.
  const guessChapterName = convGuessChapterName;

  // Build folder list with page offsets from scannedFiles
  chapterMap = {}; // folder -> {offset, name, suggested}
  if (scannedFiles && scannedFiles.length > 0) {
    let pageIdx = 0;
    scannedFiles.forEach(f => {
      const folder = f.folder || '';
      const rel = _convNormPath(f.relPath);
      const isExcluded = !!S.convExcluded[rel];
      if (!(folder in chapterMap)) {
        const suggested = guessChapterName(folder);
        chapterMap[folder] = {offset: pageIdx, name: '', suggested, excluded: isExcluded};
      } else if (chapterMap[folder].excluded && !isExcluded) {
        chapterMap[folder].offset = pageIdx;
        chapterMap[folder].excluded = false;
      }
      pageIdx++;
    });
  }
  // Populate chapter anchors from existing ComicInfo Pages/Bookmarks
  if (existing._bookmarks) {
    existing._bookmarks.forEach(([pageIdx, name]) => {
      if (!scannedFiles || !scannedFiles[pageIdx]) return;
      const folder = scannedFiles[pageIdx].folder || '';
      if (!(folder in chapterMap)) return;
      chapterMap[folder].offset = pageIdx;
      if (name) chapterMap[folder].name = name;
    });
  }
  // Populate from S.convBookmarks (user-set bookmarks from preview toolbar).
  // This must override existing ComicInfo mapping so TOC reflects sidebar edits
  // (including moving chapter start from first page to another page in folder).
  if (S.convBookmarks && scannedFiles) {
    // Pick one main bookmark per folder:
    // manual bookmarks win over auto folder bookmarks; then prefer included pages.
    const bestBmByFolder = {};
    const isBetterBookmark = (cand, prev) => {
      if (!prev) return true;
      if (cand.isManual !== prev.isManual) return cand.isManual;
      if (cand.isExcluded !== prev.isExcluded) return !cand.isExcluded;
      return cand.idx < prev.idx;
    };
    scannedFiles.forEach((f, i) => {
      const bmName = S.convBookmarks[f.relPath];
      if (!bmName) return;
      const folder = f.folder || '';
      if (!(folder in chapterMap)) return;
      const prev = bestBmByFolder[folder];
      const rp = _convNormPath(f.relPath);
      const cand = {
        idx: i,
        name: bmName,
        isManual: _convBookmarkOriginOf(rp) !== 'auto',
        isExcluded: !!S.convExcluded[rp]
      };
      if (isBetterBookmark(cand, prev)) {
        bestBmByFolder[folder] = cand;
      }
    });
    Object.entries(bestBmByFolder).forEach(([folder, bm]) => {
      chapterMap[folder].offset = bm.idx;
      chapterMap[folder].name = bm.name;
    });
  }

  hasFolders = Object.keys(chapterMap).length > 1 ||
    (Object.keys(chapterMap).length === 1 && Object.keys(chapterMap)[0] !== '');

  // For folder sources: keep additional bookmarks inside chapters (multiple TOC rows per chapter).
  if (hasFolders && scannedFiles) {
    const seen = {};
    scannedFiles.forEach((f, i) => {
      const bmName = S.convBookmarks && S.convBookmarks[f.relPath];
      if (!bmName) return;
      const folder = f.folder || '';
      if (!folder || !(folder in chapterMap)) return;
      const isMain = chapterMap[folder].offset === i;
      if (isMain) return;
      const rp = _convNormPath(f.relPath);
      if (seen[rp]) return;
      seen[rp] = true;
      folderExtraBookmarks.push({idx: i, relPath: rp, name: bmName});
    });
    if (existing._anchorBookmarks && existing._anchorBookmarks.length) {
      existing._anchorBookmarks.forEach(bm => {
        const rp = _convNormPath((bm && bm.relPath) || '');
        const name = ((bm && bm.name) || '').trim();
        if (!rp || !name || seen[rp]) return;
        const i = scannedFiles.findIndex(f => _convNormPath(f.relPath) === rp);
        if (i < 0) return;
        const folder = scannedFiles[i].folder || '';
        if (!folder || !(folder in chapterMap)) return;
        const isMain = chapterMap[folder].offset === i;
        if (isMain) return;
        seen[rp] = true;
        folderExtraBookmarks.push({idx: i, relPath: rp, name});
      });
    }
    folderExtraBookmarks.sort((a,b)=>a.idx-b.idx);
  }

  // For flat sources (PDF, flat archive) - build bookmark entries from S.convBookmarks
  flatBookmarks = []; // [{idx, relPath, name}]
  isFlat = !hasFolders;
  if (isFlat && scannedFiles) {
    scannedFiles.forEach((f, i) => {
      if (S.convBookmarks && S.convBookmarks[f.relPath]) {
        flatBookmarks.push({idx: i, relPath: f.relPath, name: S.convBookmarks[f.relPath]});
      }
    });
    // Also load from anchor-based sidecar bookmarks
    if (existing._anchorBookmarks && existing._anchorBookmarks.length) {
      existing._anchorBookmarks.forEach(bm => {
        if (bm && bm.relPath && bm.name) {
          const i = scannedFiles.findIndex(f => f.relPath === bm.relPath);
          if (i >= 0 && !flatBookmarks.some(b=>b.idx===i)) {
            flatBookmarks.push({idx: i, relPath: bm.relPath, name: bm.name});
          }
        }
      });
    }
    // Also load from existing ComicInfo bookmarks
    if (existing._bookmarks) {
      existing._bookmarks.forEach(([pageIdx, name]) => {
        if (scannedFiles[pageIdx] && !flatBookmarks.some(b=>b.idx===pageIdx)) {
          flatBookmarks.push({idx: pageIdx, relPath: scannedFiles[pageIdx].relPath, name});
        }
      });
    }
    flatBookmarks.sort((a,b) => a.idx - b.idx);
  }

  if (hasFolders) {
    const chHdr = document.createElement('div');
    Object.assign(chHdr.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem',padding:'0.5rem 0 0.1rem'});
    const chTitle = document.createElement('div');
    Object.assign(chTitle.style, {fontSize:'0.6rem',fontWeight:'700',textTransform:'uppercase',letterSpacing:'0.8px',color:'var(--text3)'});
    chTitle.textContent = t('toc.section_title', 'Table of Contents \u2014 Chapter Names');
    const chRight = document.createElement('div');
    Object.assign(chRight.style, {display:'flex',alignItems:'center',gap:'0.5rem'});
    const chHint = document.createElement('div');
    Object.assign(chHint.style, {fontSize:'0.58rem',color:'var(--text3)',opacity:'0.7'});
    chHint.textContent = t('toc.hint', 'Folder \u2192 TOC label (leave blank to use suggestion)');
    const searchBtn = document.createElement('button');
    Object.assign(searchBtn.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
      borderRadius:'var(--radius-xs)',color:'var(--text2)',cursor:'pointer',display:'inline-flex',
      alignItems:'center',justifyContent:'center',padding:'0.22rem 0.34rem',transition:'all .2s'});
    searchBtn.title = t('toc.search_title', 'Find chapter names on a web page');
    searchBtn.append(convMagnifierIcon());
    searchBtn.onmouseenter = () => { searchBtn.style.color='var(--text)'; searchBtn.style.borderColor='var(--accent)'; };
    searchBtn.onmouseleave = () => { searchBtn.style.color='var(--text2)'; searchBtn.style.borderColor='var(--glass-border)'; };
    searchBtn.onclick = () => { if (openChapterSearch) openChapterSearch(); };
    chRight.append(chHint, searchBtn);
    chHdr.append(chTitle, chRight);
    modal.append(chHdr);

    // Scrollable chapters table
    const chWrap = document.createElement('div');
    Object.assign(chWrap.style, {overflow:'hidden auto',margin:'0 -1.5rem',padding:'0 1.5rem',maxHeight:'13.5rem'});
    const chGrid = document.createElement('div');
    Object.assign(chGrid.style, {display:'grid',gridTemplateColumns:'minmax(11rem, 14rem) 1fr',gap:'0.28rem 0.6rem',alignItems:'center',paddingBottom:'0.3rem'});
    const chapterInputs = {};
    const chapterFolderTitle = folder => {
      const p = (folder || '').replace(/\\/g,'/').split('/').filter(Boolean);
      return p.length ? p[p.length - 1] : folder;
    };

    const allMatchFolderNames = () => Object.entries(chapterMap)
      .filter(([folder]) => folder !== '')
      .every(([folder, ch]) => (ch.name || '').trim() === chapterFolderTitle(folder));

    getCopyFoldersLabel = () => allMatchFolderNames()
      ? 'Revert auto names'
      : 'Copy folder names';

    Object.entries(chapterMap).forEach(([folder, ch], i) => {
      // Encoding-normalized comment.
      if (folder === '') return;
      const folderName = folder;
      // Folder label
      const lbl = document.createElement('div');
      Object.assign(lbl.style, {display:'flex',flexDirection:'column',gap:'0.08rem',minWidth:0,padding:'0.2rem 0'});
      lbl.title = folderName;
      const lblMain = document.createElement('div');
      Object.assign(lblMain.style, {fontSize:'0.68rem',color:'var(--text2)',whiteSpace:'nowrap',overflow:'hidden',
        textOverflow:'ellipsis',fontFamily:'var(--font-mono)'});
      lblMain.textContent = folderName;
      // Page offset badge
      const badge = document.createElement('span');
      Object.assign(badge.style, {fontSize:'0.52rem',color:'var(--text3)',background:'var(--glass2)',
        border:'1px solid var(--glass-border)',borderRadius:'4px',padding:'0.04rem 0.28rem',display:'inline-flex',width:'fit-content'});
      badge.textContent = 'p.' + ch.offset;
      const lblMeta = document.createElement('div');
      Object.assign(lblMeta.style, {display:'flex',alignItems:'center',gap:'0.32rem',minWidth:0});
      lblMeta.append(badge);
      lbl.append(lblMain, lblMeta);
      chGrid.append(lbl);

      // Name input
      const inp = document.createElement('input');
      Object.assign(inp.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
        borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.72rem',fontFamily:'inherit',
        outline:'none',padding:'0.25rem 0.5rem',width:'100%',boxSizing:'border-box',transition:'border-color .15s'});
      // Encoding-normalized comment.
      inp.placeholder = ch.suggested || folderName;
      inp.value = ch.name;
      inp.addEventListener('input', () => {
        ch.name = inp.value;
        if (typeof refreshCopyFolderBtn === 'function') refreshCopyFolderBtn();
        if (typeof refreshTocSeparatorBtn === 'function') refreshTocSeparatorBtn();
      });
      inp.onfocus = () => { inp.style.borderColor='var(--accent)'; };
      inp.onblur  = () => { inp.style.borderColor='var(--glass-border)'; };
      chapterInputs[folder] = inp;
      chGrid.append(inp);
    });

    applyFolderNames = () => {
      if (allMatchFolderNames()) {
        Object.entries(chapterMap).forEach(([folder, ch]) => {
          if (folder === '') return;
          ch.name = '';
          if (chapterInputs[folder]) chapterInputs[folder].value = '';
        });
        canRevertFolderNames = false;
        restoreFolderNames = null;
        return;
      }
      restoreFolderNames = {};
      Object.entries(chapterMap).forEach(([folder, ch]) => {
        if (folder === '') return;
        restoreFolderNames[folder] = ch.name || '';
      });
      Object.entries(chapterMap).forEach(([folder, ch]) => {
        if (folder === '') return;
        const v = chapterFolderTitle(folder);
        ch.name = v;
        if (chapterInputs[folder]) chapterInputs[folder].value = v;
      });
      canRevertFolderNames = true;
    };

    const splitTocTitle = value => {
      const s = String(value || '').trim();
      const explicit = s.match(/^(.+?\d)\s*([-:\u2013\u2014])\s+(\S.*)$/);
      const spaced = s.match(/^(.+?\d)\s+(\S.*)$/);
      const m = explicit
        ? [explicit[0], explicit[1], explicit[2], explicit[3]]
        : (spaced ? [spaced[0], spaced[1], ' ', spaced[2]] : null);
      if (!m) return null;
      return {prefix: m[1], sep: m[2].includes(':') ? ': ' : ' - ', suffix: m[3]};
    };
    const effectiveChapterTitle = (folder, ch) => (ch.name || '').trim() || ch.suggested || chapterFolderTitle(folder);
    const detectTocSeparatorTarget = () => {
      let dash = 0;
      let colon = 0;
      Object.entries(chapterMap).forEach(([folder, ch]) => {
        if (folder === '') return;
        const parts = splitTocTitle(effectiveChapterTitle(folder, ch));
        if (!parts) return;
        if (parts.sep === ' - ') dash += 1;
        if (parts.sep === ': ') colon += 1;
      });
      return dash >= colon ? ': ' : ' - ';
    };
    getTocSeparatorLabel = () => detectTocSeparatorTarget() === ': '
      ? t('toc.separator_to_colon', 'Use : separator')
      : t('toc.separator_to_dash', 'Use - separator');
    toggleTocSeparator = () => {
      const targetSep = detectTocSeparatorTarget();
      Object.entries(chapterMap).forEach(([folder, ch]) => {
        if (folder === '') return;
        const parts = splitTocTitle(effectiveChapterTitle(folder, ch));
        if (!parts || parts.sep === targetSep) return;
        const v = parts.prefix + targetSep + parts.suffix;
        ch.name = v;
        if (chapterInputs[folder]) chapterInputs[folder].value = v;
      });
      if (typeof refreshCopyFolderBtn === 'function') refreshCopyFolderBtn();
      if (typeof refreshTocSeparatorBtn === 'function') refreshTocSeparatorBtn();
    };

    // Chapter-name search: read a chapter list off a web page and match it to
    // these folders by chapter number, or by order within the source's volume.
    openChapterSearch = () => {
      const back = document.createElement('div');
      Object.assign(back.style, {position:'fixed',inset:'0',background:'rgba(0,0,0,0.55)',
        backdropFilter:'blur(6px)',WebkitBackdropFilter:'blur(6px)',zIndex:'10010',
        display:'flex',alignItems:'center',justifyContent:'center'});
      const panel = document.createElement('div');
      Object.assign(panel.style, {background:'var(--bg2)',border:'1px solid var(--glass-border2)',
        borderRadius:'var(--radius)',padding:'1.1rem 1.25rem',width:'min(520px,92vw)',maxHeight:'80vh',
        boxShadow:'0 24px 80px rgba(0,0,0,0.55)',display:'flex',flexDirection:'column',gap:'0.7rem',
        overflow:'hidden'});
      const closePanel = () => {
        document.removeEventListener('keydown', onPanelKey, true);
        back.remove();
      };
      // Captured, so Escape closes this panel without also closing the TOC modal
      // whose own listener sits on document.
      const onPanelKey = e => {
        if (e.key !== 'Escape') return;
        e.stopImmediatePropagation();
        closePanel();
      };
      document.addEventListener('keydown', onPanelKey, true);
      back.onclick = e => { if (e.target === back) closePanel(); };

      const headWrap = document.createElement('div');
      const head = document.createElement('div');
      Object.assign(head.style, {fontSize:'0.8rem',fontWeight:'600',color:'var(--text)'});
      head.textContent = t('toc.search_heading', 'Find chapter names');
      const sub = document.createElement('div');
      Object.assign(sub.style, {fontSize:'0.6rem',color:'var(--text3)',marginTop:'2px'});
      sub.textContent = t('toc.search_sub', 'Paste a link to a page that lists the chapters');
      headWrap.append(head, sub);

      const urlRow = document.createElement('div');
      Object.assign(urlRow.style, {display:'flex',gap:'0.4rem'});
      const urlInp = document.createElement('input');
      Object.assign(urlInp.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
        borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.72rem',fontFamily:'inherit',
        outline:'none',padding:'0.35rem 0.55rem',flex:'1',minWidth:'0',boxSizing:'border-box',
        transition:'border-color .15s'});
      urlInp.type = 'url';
      urlInp.placeholder = 'https://...';
      urlInp.onfocus = () => { urlInp.style.borderColor='var(--accent)'; };
      urlInp.onblur  = () => { urlInp.style.borderColor='var(--glass-border)'; };
      const findBtn = mkFBtn(t('toc.search_find','Find'), true, () => runSearch());
      urlInp.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); runSearch(); }
      });
      urlRow.append(urlInp, findBtn);

      // Volume of the page to match against, and how to match inside it.
      // Shown only for a page that has volumes; hidden, the panel is as before.
      const modeRow = document.createElement('div');
      Object.assign(modeRow.style, {display:'none',alignItems:'center',gap:'0.4rem',
        fontSize:'0.62rem',color:'var(--text3)'});
      const mkSelect = () => {
        const sel = document.createElement('select');
        Object.assign(sel.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
          borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.68rem',fontFamily:'inherit',
          outline:'none',padding:'0.25rem 0.4rem',minWidth:'0'});
        return sel;
      };
      const volLbl = document.createElement('span');
      volLbl.textContent = t('toc.search_volume', 'Volume');
      const volSel = mkSelect();
      const modeSel = mkSelect();
      [['order', t('toc.search_by_order', 'by order in volume')],
       ['number', t('toc.search_by_number', 'by number')]].forEach(([value, label]) => {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = label;
        modeSel.append(opt);
      });
      volSel.onchange = () => {
        const whole = volSel.value === '';
        if (whole) modeSel.value = 'number';
        else if (modeSel.disabled) modeSel.value = 'order';
        modeSel.disabled = whole;
        rematch();
      };
      modeSel.onchange = () => rematch();
      modeRow.append(volLbl, volSel, modeSel);

      const status = document.createElement('div');
      Object.assign(status.style, {fontSize:'0.62rem',color:'var(--text3)',minHeight:'0.9rem'});

      const listWrap = document.createElement('div');
      Object.assign(listWrap.style, {overflow:'hidden auto',margin:'0 -1.25rem',padding:'0 1.25rem',
        maxHeight:'15rem',display:'none'});
      const listGrid = document.createElement('div');
      Object.assign(listGrid.style, {display:'grid',gridTemplateColumns:'minmax(9rem, 12rem) 1fr',
        gap:'0.24rem 0.6rem',alignItems:'center',paddingBottom:'0.3rem'});
      listWrap.append(listGrid);

      const foot = document.createElement('div');
      Object.assign(foot.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem'});
      const count = document.createElement('div');
      Object.assign(count.style, {fontSize:'0.62rem',color:'var(--text3)',flex:'1'});
      const footBtns = document.createElement('div');
      Object.assign(footBtns.style, {display:'flex',gap:'0.4rem'});
      const applyBtn = mkFBtn(t('toc.search_apply','Apply'), true, () => applyMatches());
      applyBtn.style.display = 'none';
      footBtns.append(mkFBtn(t('toc.search_cancel','Cancel'), false, () => closePanel()), applyBtn);
      foot.append(count, footBtns);

      panel.append(headWrap, urlRow, modeRow, status, listWrap, foot);
      back.append(panel);
      document.body.append(back);
      setTimeout(() => urlInp.focus(), 40);

      let rows = [];
      let chapters = [];
      let baseNote = '';
      let baseWarn = false;

      const showError = message => {
        status.style.color = 'var(--red)';
        status.textContent = message;
      };

      // The folder's own number is what the reader will look for; the page's
      // number stands in only where the folder has none.
      const chapterName = (found, folderNumber) => {
        const label = (found.label || t('toc.chapter','Chapter')).trim();
        const title = (found.title || '').trim();
        const number = folderNumber === null ? found.number : folderNumber;
        const head = (label ? label + ' ' : '') + number;
        return title ? head + ': ' + title : head;
      };

      const sourceFolders = () => Object.keys(chapterMap).filter(folder => folder !== '');

      const pageVolumes = () => {
        const seen = new Set();
        chapters.forEach(c => { if (c.volume !== null && c.volume !== undefined) seen.add(c.volume); });
        return [...seen].sort((a, b) => a - b);
      };

      const matchWholePage = folders => {
        const byNumber = {};
        chapters.forEach(c => { if (!(c.number in byNumber)) byNumber[c.number] = c; });
        const matched = folders.map(folder => {
          const number = convChapterNumber(folder);
          if (number === null) return {folder, state:'nonumber'};
          const found = byNumber[number];
          if (!found) return {folder, state:'missing'};
          return {folder, state:'ok', name: chapterName(found, number)};
        });
        return {rows: matched, extra: 0};
      };

      // Inside a volume: the i-th folder is the i-th chapter ('order'), or the
      // folder's number is the chapter's number within the volume ('number').
      const matchInVolume = (folders, volume, mode) => {
        const pool = chapters.filter(c => c.volume === volume).sort((a, b) => a.number - b.number);
        const byNumber = {};
        pool.forEach(c => { if (!(c.number in byNumber)) byNumber[c.number] = c; });
        const matched = folders.map((folder, i) => {
          const number = convChapterNumber(folder);
          if (mode === 'number' && number === null) return {folder, state:'nonumber'};
          const found = mode === 'order' ? pool[i] : byNumber[number];
          if (!found) return {folder, state:'missing'};
          return {folder, state:'ok', name: chapterName(found, number)};
        });
        const extra = mode === 'order' ? Math.max(0, pool.length - folders.length) : 0;
        return {rows: matched, extra};
      };

      const renderRows = () => {
        listGrid.textContent = '';
        rows.forEach(row => {
          const lbl = document.createElement('div');
          Object.assign(lbl.style, {fontSize:'0.65rem',color:'var(--text2)',whiteSpace:'nowrap',
            overflow:'hidden',textOverflow:'ellipsis',fontFamily:'var(--font-mono)'});
          lbl.textContent = row.folder;
          lbl.title = row.folder;
          const val = document.createElement('div');
          Object.assign(val.style, {fontSize:'0.68rem',whiteSpace:'nowrap',overflow:'hidden',
            textOverflow:'ellipsis'});
          if (row.state === 'ok') {
            val.style.color = 'var(--text)';
            val.textContent = row.name;
          } else {
            val.style.color = 'var(--text3)';
            val.style.fontStyle = 'italic';
            val.textContent = row.state === 'nonumber'
              ? t('toc.search_no_number', 'chapter number not recognised')
              : t('toc.search_not_found', 'not on the page');
          }
          listGrid.append(lbl, val);
        });
      };

      // Re-runs matching against the chapters already in memory whenever the
      // volume or the mode changes; the page is not fetched again.
      const rematch = () => {
        const folders = sourceFolders();
        const volume = volSel.value === '' ? null : Number(volSel.value);
        const {rows: result, extra} = volume === null
          ? matchWholePage(folders)
          : matchInVolume(folders, volume, modeSel.value);
        rows = result;
        renderRows();
        const matched = rows.filter(row => row.state === 'ok').length;
        const more = extra
          ? t('toc.search_more_on_page', '{n} more chapters on the page').replace('{n}', extra)
          : '';
        status.style.color = baseWarn ? 'var(--red)' : 'var(--text3)';
        status.textContent = baseNote && more ? baseNote + ' · ' + more : baseNote || more;
        listWrap.style.display = 'block';
        count.textContent = t('toc.search_matched', 'Matched') + ' ' + matched + ' / ' + rows.length;
        applyBtn.style.display = matched ? '' : 'none';
      };

      // A page split into volumes is matched to the volume this source is,
      // by order; anything else falls back to the whole page by number.
      const showRows = (found, note, warn) => {
        chapters = found || [];
        baseNote = note || '';
        baseWarn = !!warn;
        const volumes = pageVolumes();
        volSel.textContent = '';
        const whole = document.createElement('option');
        whole.value = '';
        whole.textContent = t('toc.search_whole_page', '— whole page');
        volSel.append(whole);
        volumes.forEach(volume => {
          const opt = document.createElement('option');
          opt.value = String(volume);
          opt.textContent = String(volume);
          volSel.append(opt);
        });
        const own = convVolumeNumber(source);
        const auto = own !== null && volumes.includes(own);
        volSel.value = auto ? String(own) : '';
        modeSel.value = auto ? 'order' : 'number';
        modeSel.disabled = !auto;
        modeRow.style.display = volumes.length ? 'flex' : 'none';
        rematch();
      };

      // Opening the panel reads the file the last scrape left beside the source,
      // so a volume added later needs no link at all.
      const loadStored = async () => {
        status.style.color = 'var(--text3)';
        status.textContent = t('toc.search_reading_file', 'Reading chapter_names.json…');
        let data = null;
        try {
          data = await (await apiPost('/api/toc/chapter-names', {source})).json();
        } catch (error) {
          data = null;
        }
        if (!data || !data.ok || !data.exists) {
          if (data && data.warning) showError(data.warning);
          else status.textContent = '';
          return;
        }
        if (data.url) urlInp.value = data.url;
        const when = (data.updated || '').slice(0, 10);
        showRows(data.chapters || [],
          t('toc.search_from_file', 'from chapter_names.json') + (when ? ' · ' + when : ''));
      };

      const runSearch = async () => {
        const url = urlInp.value.trim();
        if (!url) { showError(t('toc.search_need_url', 'Paste a link first')); return; }
        findBtn.disabled = true;
        findBtn.style.opacity = '0.6';
        listWrap.style.display = 'none';
        modeRow.style.display = 'none';
        applyBtn.style.display = 'none';
        count.textContent = '';
        status.style.color = 'var(--text3)';
        status.textContent = t('toc.search_loading', 'Loading the page…');
        let data = null;
        try {
          data = await (await apiPost('/api/toc/scrape', {url, source})).json();
        } catch (error) {
          data = {ok:false, error:error.message};
        }
        findBtn.disabled = false;
        findBtn.style.opacity = '1';
        if (!data || !data.ok) {
          showError((data && data.error) || t('toc.search_failed', 'Could not read that page'));
          return;
        }
        const note = data.saveError
          ? t('toc.search_not_saved', 'Names not saved:') + ' ' + data.saveError
          : t('toc.search_saved', 'Saved to chapter_names.json');
        showRows(data.chapters || [], note, !!data.saveError);
      };

      const applyMatches = () => {
        let applied = 0;
        rows.forEach(row => {
          if (row.state !== 'ok') return;
          const ch = chapterMap[row.folder];
          if (!ch) return;
          ch.name = row.name;
          if (chapterInputs[row.folder]) chapterInputs[row.folder].value = row.name;
          applied += 1;
        });
        if (typeof refreshCopyFolderBtn === 'function') refreshCopyFolderBtn();
        if (typeof refreshTocSeparatorBtn === 'function') refreshTocSeparatorBtn();
        closePanel();
        if (statusEl) {
          statusEl.style.color = 'var(--text3)';
          statusEl.textContent = t('toc.search_applied', 'Filled in') + ' ' + applied;
        }
      };

      loadStored();
    };

    chWrap.append(chGrid);
    modal.append(chWrap);

    // Additional TOC rows inside chapter folders
    const exDiv = document.createElement('div');
    Object.assign(exDiv.style, {height:'1px',background:'var(--glass-border)',margin:'0 -1.5rem'});
    modal.append(exDiv);

    const exHdr = document.createElement('div');
    Object.assign(exHdr.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem',padding:'0.5rem 0 0.1rem'});
    const exTitle = document.createElement('div');
    Object.assign(exTitle.style, {fontSize:'0.6rem',fontWeight:'700',textTransform:'uppercase',letterSpacing:'0.8px',color:'var(--text3)'});
    exTitle.textContent = 'Extra TOC rows from sidebar bookmarks';
    const exHint = document.createElement('div');
    Object.assign(exHint.style, {fontSize:'0.58rem',color:'var(--text3)',opacity:'0.7'});
    exHint.textContent = 'Add bookmarks in sidebar preview';
    exHdr.append(exTitle, exHint);
    modal.append(exHdr);

    const exWrap = document.createElement('div');
    Object.assign(exWrap.style, {overflow:'hidden auto',margin:'0 -1.5rem',padding:'0 1.5rem',maxHeight:'7.5rem'});
    const exGrid = document.createElement('div');
    Object.assign(exGrid.style, {display:'grid',gridTemplateColumns:'auto auto 1fr auto',gap:'0.28rem 0.45rem',alignItems:'center',paddingBottom:'0.3rem'});

    const renderExtraRows = () => {
      exGrid.innerHTML = '';
      if (!folderExtraBookmarks.length) {
        const hint = document.createElement('div');
        Object.assign(hint.style, {gridColumn:'1/-1',fontSize:'0.66rem',color:'var(--text3)',padding:'0.35rem 0',fontStyle:'italic'});
        hint.textContent = 'You can add multiple TOC rows inside one chapter.';
        exGrid.append(hint);
        return;
      }
      folderExtraBookmarks.forEach((bm, rowIdx) => {
        const pageLbl = document.createElement('span');
        Object.assign(pageLbl.style, {fontSize:'0.62rem',color:'var(--text3)',fontFamily:'var(--font-mono)'});
        pageLbl.textContent = 'p.';
        exGrid.append(pageLbl);

        const pageInp = document.createElement('input');
        pageInp.type = 'number';
        pageInp.min = '1';
        pageInp.max = String(scannedFiles.length);
        pageInp.value = String((bm.idx||0) + 1);
        Object.assign(pageInp.style, {width:'4.1rem',background:'var(--glass2)',border:'1px solid var(--glass-border)',
          borderRadius:'6px',color:'var(--text)',fontSize:'0.68rem',padding:'0.2rem 0.35rem',outline:'none',boxSizing:'border-box'});
        pageInp.onchange = () => {
          let v = parseInt(pageInp.value, 10);
          if (!Number.isFinite(v)) v = 1;
          v = Math.max(1, Math.min(scannedFiles.length, v));
          bm.idx = v - 1;
          bm.relPath = scannedFiles[bm.idx] ? scannedFiles[bm.idx].relPath : bm.relPath;
          pageInp.value = String(v);
        };
        exGrid.append(pageInp);

        const nameInp = document.createElement('input');
        Object.assign(nameInp.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
          borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.72rem',fontFamily:'inherit',
          outline:'none',padding:'0.25rem 0.5rem',width:'100%',boxSizing:'border-box',transition:'border-color .15s'});
        nameInp.value = bm.name || '';
        nameInp.oninput = () => { bm.name = nameInp.value; };
        nameInp.onfocus = () => { nameInp.style.borderColor='var(--accent)'; };
        nameInp.onblur  = () => { nameInp.style.borderColor='var(--glass-border)'; };
        exGrid.append(nameInp);

        const del = document.createElement('button');
        Object.assign(del.style, {background:'rgba(248,113,113,0.1)',border:'1px solid rgba(248,113,113,0.25)',
          borderRadius:'6px',color:'var(--red)',cursor:'pointer',fontSize:'0.65rem',padding:'0.2rem 0.42rem',transition:'all .2s'});
        del.textContent = '✕';
        del.onclick = () => {
          folderExtraBookmarks.splice(rowIdx, 1);
          renderExtraRows();
        };
        exGrid.append(del);
      });
    };
    renderExtraRows();

    exWrap.append(exGrid);
    modal.append(exWrap);
  }

  // For flat sources: show user-defined page bookmarks
  if (isFlat && scannedFiles && scannedFiles.length > 0) {
    const fbDiv0 = document.createElement('div');
    Object.assign(fbDiv0.style, {height:'1px',background:'var(--glass-border)',margin:'0 -1.5rem'});
    modal.append(fbDiv0);

    const fbHdr = document.createElement('div');
    Object.assign(fbHdr.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem',padding:'0.5rem 0 0.1rem'});
    const fbTitle = document.createElement('div');
    Object.assign(fbTitle.style, {fontSize:'0.6rem',fontWeight:'700',textTransform:'uppercase',letterSpacing:'0.8px',color:'var(--text3)'});
    fbTitle.textContent = 'Bookmarks \u2014 Chapter Markers';
    const fbHint = document.createElement('div');
    Object.assign(fbHint.style, {fontSize:'0.58rem',color:'var(--text3)',opacity:'0.7'});
    fbHint.textContent = 'Set bookmarks on pages via Bookmark in preview toolbar';
    fbHdr.append(fbTitle, fbHint);
    modal.append(fbHdr);

    const fbWrap = document.createElement('div');
    Object.assign(fbWrap.style, {overflow:'hidden auto',margin:'0 -1.5rem',padding:'0 1.5rem',maxHeight:'9rem'});
    const fbGrid = document.createElement('div');
    Object.assign(fbGrid.style, {display:'grid',gridTemplateColumns:'auto 1fr auto',gap:'0.3rem 0.6rem',alignItems:'center',paddingBottom:'0.3rem'});

    if (flatBookmarks.length === 0) {
      const hint = document.createElement('div');
      Object.assign(hint.style, {gridColumn:'1/-1',fontSize:'0.68rem',color:'var(--text3)',padding:'0.4rem 0',fontStyle:'italic'});
      hint.textContent = 'No bookmarks yet. Open a page in preview and click Bookmark to add chapters.';
      fbGrid.append(hint);
    } else {
      flatBookmarks.forEach(bm => {
        // Page badge
        const lbl = document.createElement('div');
        Object.assign(lbl.style, {fontSize:'0.68rem',color:'var(--text2)',whiteSpace:'nowrap',fontFamily:'var(--font-mono)',padding:'0.25rem 0'});
        lbl.textContent = 'p.' + (bm.idx + 1);
        fbGrid.append(lbl);
        // Name input
        const inp = document.createElement('input');
        Object.assign(inp.style, {background:'var(--glass2)',border:'1px solid var(--glass-border)',
          borderRadius:'var(--radius-xs)',color:'var(--text)',fontSize:'0.72rem',fontFamily:'inherit',
          outline:'none',padding:'0.25rem 0.5rem',width:'100%',boxSizing:'border-box',transition:'border-color .15s'});
        inp.value = bm.name;
        inp.addEventListener('input', () => { bm.name = inp.value; });
        inp.onfocus = () => { inp.style.borderColor='var(--accent)'; };
        inp.onblur  = () => { inp.style.borderColor='var(--glass-border)'; };
        fbGrid.append(inp);
        // Delete button
        const del = document.createElement('button');
        Object.assign(del.style, {background:'rgba(248,113,113,0.1)',border:'1px solid rgba(248,113,113,0.25)',
          borderRadius:'6px',color:'var(--red)',cursor:'pointer',fontSize:'0.65rem',padding:'0.2rem 0.4rem',transition:'all .2s'});
        del.textContent = '\u2715';
        del.onclick = () => {
          _convDeleteBookmark(bm.relPath, source, true);
          flatBookmarks.splice(flatBookmarks.indexOf(bm), 1);
          del.parentElement.removeChild(del);
          inp.parentElement.removeChild(inp);
          lbl.parentElement.removeChild(lbl);
        };
        fbGrid.append(del);
      });
    }
    fbWrap.append(fbGrid);
    modal.append(fbWrap);
  }
  }

  // Divider
  const div1 = document.createElement('div');
  Object.assign(div1.style, {height:'1px',background:'var(--glass-border)',margin:'0 -1.5rem'});
  modal.append(div1);

  // Footer: status + buttons
  const footer = document.createElement('div');
  Object.assign(footer.style, {display:'flex',alignItems:'center',justifyContent:'space-between',gap:'0.5rem'});
  const statusEl = document.createElement('div');
  Object.assign(statusEl.style, {fontSize:'0.62rem',color:'var(--text3)',flex:'1'});
  footer.append(statusEl);

  const btnRow = document.createElement('div');
  Object.assign(btnRow.style, {display:'flex',gap:'0.4rem'});

  const mkFBtn = (label, accent, fn) => {
    const b = document.createElement('button');
    Object.assign(b.style, {background:accent?'var(--accent)':'var(--glass2)',
      border:'1px solid '+(accent?'var(--accent)':'var(--glass-border)'),borderRadius:'var(--radius-xs)',
      color:accent?'#fff':'var(--text2)',fontSize:'0.72rem',fontFamily:'inherit',padding:'0.35rem 0.85rem',
      cursor:'pointer',transition:'all .2s',fontWeight:accent?'600':'400'});
    b.textContent = label;
    b.onmouseenter=()=>{b.style.opacity='0.85';};
    b.onmouseleave=()=>{b.style.opacity='1';};
    b.onclick = fn;
    return b;
  };

  if (isTocMode && hasFolders && typeof applyFolderNames === 'function') {
    const copyBtn = mkFBtn(getCopyFoldersLabel(), false, () => {
      applyFolderNames();
      refreshCopyFolderBtn();
      if (typeof refreshTocSeparatorBtn === 'function') refreshTocSeparatorBtn();
    });
    refreshCopyFolderBtn = () => { copyBtn.textContent = getCopyFoldersLabel(); };
    refreshCopyFolderBtn();
    btnRow.append(copyBtn);
    if (typeof toggleTocSeparator === 'function') {
      const sepBtn = mkFBtn(getTocSeparatorLabel(), false, () => {
        toggleTocSeparator();
      });
      refreshTocSeparatorBtn = () => { sepBtn.textContent = getTocSeparatorLabel(); };
      refreshTocSeparatorBtn();
      btnRow.append(sepBtn);
    }
  } else {
    btnRow.append(mkFBtn('Cancel', false, close));
  }
  btnRow.append(mkFBtn(isTocMode?'Save TOC':'Save ComicInfo.xml', true, async () => {
    statusEl.textContent = 'Saving...';
    statusEl.style.color = 'var(--text3)';
    try {
      const fields = {};
      if (isTocMode) {
        // Preserve existing metadata fields in TOC-only mode.
        Object.entries(existing || {}).forEach(([k,v]) => {
          if (!k.startsWith('_') && v != null && String(v).trim() !== '') fields[k] = String(v).trim();
        });
      } else {
        FIELDS.forEach(([key]) => { if(vals[key] && vals[key].trim()) fields[key] = vals[key].trim(); });
      }
      // Build bookmarks from chapterMap (folder sources) or flatBookmarks (flat sources)
      let bookmarks = [];
      if (isTocMode && hasFolders) {
        const primaryBookmarks = Object.entries(chapterMap)
          .sort((a,b) => a[1].offset - b[1].offset)
          .filter(([folder, ch]) => folder !== '' && (ch.name.trim() || ch.suggested || Object.values(chapterMap).some(c=>c.name.trim()||c.suggested)))
          .map(([folder, ch]) => ({
            offset: ch.offset,
            relPath: (scannedFiles && scannedFiles[ch.offset]) ? scannedFiles[ch.offset].relPath : null,
            name: ch.name.trim() || ch.suggested || folder,
            isAuto: (!ch.name.trim() && !!ch.suggested) || (!!ch.suggested && ch.name.trim() === ch.suggested)
          }));
        const extraBookmarks = (folderExtraBookmarks || [])
          .filter(bm => bm && bm.name && bm.name.trim() && scannedFiles && scannedFiles[bm.idx])
          .map(bm => ({
            offset: bm.idx,
            relPath: scannedFiles[bm.idx].relPath,
            name: bm.name.trim()
          }));
        const byRel = {};
        [...primaryBookmarks, ...extraBookmarks].forEach(bm => {
          const key = _convNormPath(bm.relPath || '');
          if (!key) return;
          byRel[key] = bm;
        });
        bookmarks = Object.values(byRel).sort((a,b)=>a.offset-b.offset);

        // Encoding-normalized comment.
        if (scannedFiles) {
          const primaryRel = {};
          const primaryAutoRel = {};
          primaryBookmarks.forEach(bm => {
            const rp = _convNormPath(bm.relPath || '');
            if (rp) {
              primaryRel[rp] = true;
              primaryAutoRel[rp] = !!bm.isAuto;
            }
          });
          // Clear old bookmarks for this source
          scannedFiles.forEach(f => { _convDeleteBookmark(f.relPath, source, false); });
          bookmarks.forEach(bm => {
            if (scannedFiles[bm.offset]) {
              const rp = scannedFiles[bm.offset].relPath;
              const normRp = _convNormPath(rp);
              const isPrimary = !!primaryRel[normRp];
              const origin = (isPrimary && primaryAutoRel[normRp]) ? 'auto' : 'manual';
              _convSetBookmarkWithOrigin(rp, bm.name, source, origin);
            }
          });
        }
      } else if (isTocMode && isFlat) {
        bookmarks = flatBookmarks
          .filter(bm => bm.name && bm.name.trim())
          .map(bm => ({ relPath: bm.relPath, offset: bm.idx, name: bm.name.trim() }));
        // Encoding-normalized comment.
        flatBookmarks.forEach(bm => {
          if (bm.name && bm.name.trim()) {
            const prevOrigin = _convBookmarkOriginOf(bm.relPath);
            _convSetBookmarkWithOrigin(bm.relPath, bm.name.trim(), source, prevOrigin === 'auto' ? 'auto' : 'manual');
          } else _convDeleteBookmark(bm.relPath, source, true);
        });
      } else {
        // Preserve existing bookmarks in Meta-only mode.
        if (existing._anchorBookmarks && existing._anchorBookmarks.length && scannedFiles) {
          const idxByRel = {};
          scannedFiles.forEach((f, i) => { idxByRel[f.relPath] = i; });
          bookmarks = existing._anchorBookmarks
            .filter(bm => bm && bm.relPath && bm.name && idxByRel[bm.relPath] != null)
            .map(bm => ({relPath: bm.relPath, offset: idxByRel[bm.relPath], name: bm.name}));
        } else if (existing._bookmarks && existing._bookmarks.length) {
          bookmarks = existing._bookmarks.map(([offset, name]) => ({
            offset, name,
            relPath: (scannedFiles && scannedFiles[offset]) ? scannedFiles[offset].relPath : null
          }));
        }
      }
      const r = await (await apiPost('/api/comicinfo/write', {source, fields, bookmarks})).json();
      if (r.ok) {
        if (isTocMode) {
          const srcNorm = (source || '').replace(/\\/g, '/').replace(/\/+$/, '');
          const srcLeaf = srcNorm.split('/').pop() || '';
          const srcBase = srcLeaf.replace(/\.[^/.]+$/, '');
          statusEl.textContent = 'Saved TOC: ' + srcBase + '.sidecar.json';
        } else {
          statusEl.textContent = 'Saved: ' + r.path.split(/[/\\]/).slice(-1)[0];
        }
        statusEl.style.color = 'var(--accent)';
        render(); // update sidebar bookmark indicators
      } else {
        statusEl.textContent = 'Error: ' + (r.error || 'Error');
        statusEl.style.color = 'var(--red)';
      }
    } catch(e) {
      statusEl.textContent = 'Error: ' + e.message;
      statusEl.style.color = 'var(--red)';
    }
  }));

  footer.append(btnRow);
  modal.append(footer);
  overlay.append(modal);
  document.body.append(overlay);

  function close() {
    overlay.remove();
    document.removeEventListener('keydown', onKey);
  }
  const onKey = e => { if(e.key==='Escape') close(); };
  document.addEventListener('keydown', onKey);

  // Focus first field
  const first = inputs['Title'];
  if(first && !isTocMode) setTimeout(()=>first.focus(), 50);
}

function showSourceModal(){
  // Remove existing modal
  const old=document.getElementById('srcModal');if(old)old.remove();
  const overlay=document.createElement('div');overlay.id='srcModal';
  Object.assign(overlay.style,{position:'fixed',top:'0',left:'0',width:'100%',height:'100%',
    background:'rgba(0,0,0,0.55)',backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',
    zIndex:'10000',display:'flex',alignItems:'center',justifyContent:'center'});
  overlay.onclick=e=>{if(e.target===overlay)overlay.remove();};
  const closeModal=()=>{overlay.remove();document.removeEventListener('keydown',onKey);};
  const onKey=e=>{if(e.key==='Escape')closeModal();};
  document.addEventListener('keydown',onKey);
  const modal=document.createElement('div');
  Object.assign(modal.style,{background:'var(--bg2)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
    padding:'1.5rem',minWidth:'16rem',boxShadow:'0 24px 80px rgba(0,0,0,0.5)',display:'flex',flexDirection:'column',gap:'0.7rem'});
  const title=document.createElement('div');title.textContent=t('files.add_source');
  Object.assign(title.style,{fontSize:'0.85rem',fontWeight:'600',color:'var(--text)',textAlign:'center',marginBottom:'0.3rem'});
  modal.append(title);
  const mkBtn=(icon,label,sub,fn)=>{
    const btn=document.createElement('div');
    Object.assign(btn.style,{display:'flex',alignItems:'center',gap:'0.7rem',padding:'0.7rem 0.9rem',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s'});
    btn.onmouseenter=()=>{btn.style.background='var(--glass3)';btn.style.borderColor='var(--accent)';};
    btn.onmouseleave=()=>{btn.style.background='var(--glass2)';btn.style.borderColor='var(--glass-border)';};
    btn.innerHTML=`<span style="font-size:1.4rem">${icon}</span><div><div style="font-size:0.8rem;font-weight:500;color:var(--text)">${label}</div><div style="font-size:0.65rem;color:var(--text3);margin-top:1px">${sub}</div></div>`;
    btn.onclick=()=>{closeModal();fn();};
    return btn;
  };
  modal.append(mkBtn('\ud83d\udcc1',t('source_modal.folder'),t('source_modal.folder_desc'),async()=>{
    try{const r=await(await apiPost('/api/browse-source',{type:'folder',multiple:true})).json();
      await _convAddSources(browseSourcePaths(r));
    }catch(e){}
  }));
  modal.append(mkBtn('\ud83d\udce6',t('source_modal.archive'),'CBR, CBZ, ZIP, RAR, 7Z, PDF',async()=>{
    try{const r=await(await apiPost('/api/browse-source',{type:'file'})).json();
      await _convAddSources(browseSourcePaths(r));
    }catch(e){}
  }));
  // Cancel action
  const cancel=document.createElement('div');
  cancel.textContent=t('source_modal.cancel','Cancel');
  Object.assign(cancel.style,{textAlign:'center',fontSize:'0.72rem',color:'var(--text3)',cursor:'pointer',
    padding:'0.3rem',transition:'color .2s',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.2rem'});
  cancel.onmouseenter=()=>{cancel.style.color='var(--text2)';};
  cancel.onmouseleave=()=>{cancel.style.color='var(--text3)';};
  cancel.onclick=closeModal;
  modal.append(cancel);
  overlay.append(modal);document.body.append(overlay);
}
// Drag-and-drop handler for convert sidebar
function setupConvertDragDrop(el){
  if(!el||el._dndBound)return;el._dndBound=true;
  const prevent=e=>{e.preventDefault();e.stopPropagation();};
  el.addEventListener('dragover',e=>{prevent(e);el.style.borderColor='var(--accent)';el.style.background='rgba(110,170,255,0.06)';});
  el.addEventListener('dragleave',e=>{prevent(e);el.style.borderColor='';el.style.background='';});
  el.addEventListener('drop',e=>{
    prevent(e);el.style.borderColor='';el.style.background='';
    const items=e.dataTransfer.items||[];const files=e.dataTransfer.files||[];
    // Try to get paths (works in some environments like Electron/webview)
    const paths=[];
    if(items.length>0){
      for(let i=0;i<items.length;i++){
        const item=items[i];
        if(item.kind==='file'){
          const f=item.getAsFile();
          if(f&&f.path){paths.push(f.path);}
          else if(f&&f.name){
            // Browser mode: can't get path, show modal instead
            showSourceModal();return;
          }
        }
      }
    }
    if(paths.length){_convAddSources(paths);return;}
    if(files.length>0&&!S.convSources.some(s=>s.endsWith(files[0].name))){
      // File objects don't have paths in browser, fallback to modal
      showSourceModal();
    }
  });
}
async function selectConvertOutput(){
  try{const r=await(await apiPost('/api/browse-folder',{})).json();
    if(r.path){S.convOutputDir=r.path;render();}
  }catch(e){alert(e.message);}
}
// Rendering may request the same source many times. Share queued work, and
// invalidate its identity on removal so late responses cannot restore old state.
const _convSourceLoads=new Map();
const _convSourcePreparations=new Map();
let _convSourceLoadQueue=Promise.resolve();
let _convSourcePrepareQueue=Promise.resolve();
function _convSourceIsOpen(path){
  const index=S.convSources.indexOf(path);
  const collapsed=S.convCollapsed['src:'+index];
  return index>=0&&(collapsed===undefined?S.convSources.length===1:!collapsed);
}
function _convForgetSource(path){
  _convSourceLoads.delete(path);
  _convSourcePreparations.delete(path);
  _convWatermarkScans.delete(path);
  if(S._convSourceErrors)delete S._convSourceErrors[path];
}
function _convAddSources(paths){
  const added=[...new Set(paths.filter(path=>path&&!S.convSources.includes(path)))];
  if(!added.length)return Promise.resolve([]);
  const firstIndex=S.convSources.length;
  S.convSources.push(...added);
  added.forEach((path,index)=>{S.convCollapsed['src:'+(firstIndex+index)]=added.length>1;});
  S.convViewIdx=null;
  S.convExpandedSource=added.length===1?added[0]:null;
  // Register every request before render can ask for any of them again.
  const loading=Promise.all(added.map(scanConvertSource));
  if(added.length===1)_convPrepareSource(added[0]);
  render();
  return loading;
}
function scanConvertSource(path){
  if(!S.convSources.includes(path))return Promise.resolve(false);
  if(S.convScanned[path])return Promise.resolve(true);
  if(_convSourceLoads.has(path))return _convSourceLoads.get(path);
  const pending=_convSourceLoadQueue.then(()=>{
    if(_convSourceLoads.get(path)!==pending||!S.convSources.includes(path))return false;
    return _convLoadSource(path,pending);
  });
  _convSourceLoads.set(path,pending);
  _convSourceLoadQueue=pending.catch(()=>false);
  return pending;
}
function _convPrepareSource(path){
  if(_convSourcePreparations.has(path))return _convSourcePreparations.get(path);
  const pending=_convSourcePrepareQueue.then(async()=>{
    const isCurrent=()=>_convSourcePreparations.get(path)===pending&&S.convSources.includes(path);
    if(!isCurrent()||!await scanConvertSource(path)||!isCurrent())return false;
    if(!await _convDetectSpreads(path,isCurrent)||!isCurrent())return false;
    if(S.convMaicWatermarks&&!await _convAutoScanWatermarks([path]))return false;
    if(S.convMaicPageNumbers)_convScanPageNumbers(path).catch(error=>console.error(error));
    return isCurrent();
  });
  _convSourcePreparations.set(path,pending);
  _convSourcePrepareQueue=pending.catch(()=>false);
  pending.then(ok=>{
    if(!ok&&_convSourcePreparations.get(path)===pending&&S.convSources.includes(path)){
      const errors=S._convSourceErrors||(S._convSourceErrors={});
      if(!errors[path])errors[path]=t('conv.source_prepare_failed','Could not prepare source: {source}').replace('{source}',path);
      render();
    }
  });
  return pending;
}
async function _convLoadSource(path,pending){
  try{const r=await(await apiPost('/api/convert/scan-source',{path})).json();
    if(_convSourceLoads.get(path)!==pending||!S.convSources.includes(path))return false;
    if(!r.ok)throw new Error(r.error||'Source scan failed');
    if(r.ok){
      S.convScanned[path]=r.files||[];
      const files=S.convScanned[path];
      const hadBookmarksBefore=files.some(f=>!!S.convBookmarks[f.relPath]);
      let loadedBookmarks=0;
      const firstRelByFolder=_convFirstRelByFolder(files);
      (r['excluded']||[]).forEach(k=>{S.convExcluded[k]=true;});
      const detected={};
      (r['watermark-matches']||[]).forEach(k=>{const rel=_convNormPath(k);if(rel)detected[rel]=1;});
      S.convWatermarkMatches={...(S.convWatermarkMatches||{}),[path]:detected};
      S.convWatermarkReviewed={...(S.convWatermarkReviewed||{}),[path]:!!r['watermark-matches-saved']};
      // Load nocrop files from sidecar
      (r.files||[]).forEach(f=>{
        if(f['no-crop']&&f.relPath&&!S.convExclusions[f.relPath]){
          S.convExclusions[f.relPath]={'no-crop':true};
        }
      });
      // Load custom-crop from sidecar
      if(r['custom-crop']){
        Object.entries(r['custom-crop']).forEach(([k,v])=>{
          if(!S.convCustomCrop[k])S.convCustomCrop[k]=v;
        });
      }
      if(r['custom-split']){
        Object.entries(r['custom-split']).forEach(([k,v])=>{
          if(!S.convCustomSplit[k])S.convCustomSplit[k]=v;
        });
      }
      // Load extra-margin from sidecar
      if(r['extra-margin']){
        Object.entries(r['extra-margin']).forEach(([k,v])=>{
          if(!S.convExtraMargin[k]){S.convExtraMargin[k]=v;}
        });
      }
      // Load edit-ops from sidecar
      if(r['edit-ops']){
        Object.entries(r['edit-ops']).forEach(([k,v])=>{
          if(!S.convEditOps[k]&&Array.isArray(v)&&v.length)S.convEditOps[k]=v;
        });
      }
      // Load bookmarks: prefer unified sidecar anchors (stable across exclude), fallback to ComicInfo.xml numeric bookmarks
      if(r.bookmarkAnchors&&r.bookmarkAnchors.length>0){
        r.bookmarkAnchors.forEach(bm=>{
          const rp=(bm.relPath||bm.anchor_relpath||bm.anchorRelPath||'').replace(/\\/g,'/').replace(/^\//,'');
          const name=(bm.name||bm.Bookmark||bm.title||'').trim();
          if(rp&&name){
            const prevOrigin = _convBookmarkOriginOf(rp);
            const fMeta = files.find(f=>f.relPath===rp);
            const guessed = fMeta ? convGuessChapterName(fMeta.folder||'') : '';
            const isAutoByName = !!guessed && guessed === name &&
              firstRelByFolder[fMeta ? (fMeta.folder||'') : ''] === _convNormPath(rp);
            _convSetBookmarkWithOrigin(rp, name, path, (prevOrigin === 'auto' || isAutoByName) ? 'auto' : 'manual');
            loadedBookmarks++;
          }
        });
      } else if(r.bookmarks&&r.bookmarks.length>0&&r.files){
        r.bookmarks.forEach(([pageIdx,name])=>{
          if(r.files[pageIdx]&&name&&!S.convBookmarks[r.files[pageIdx].relPath]){
            const rp = r.files[pageIdx].relPath;
            const prevOrigin = _convBookmarkOriginOf(rp);
            const fMeta = r.files[pageIdx];
            const guessed = fMeta ? convGuessChapterName(fMeta.folder||'') : '';
            const isAutoByName = !!guessed && guessed === name &&
              firstRelByFolder[fMeta ? (fMeta.folder||'') : ''] === _convNormPath(rp);
            _convSetBookmarkWithOrigin(rp, name, path, (prevOrigin === 'auto' || isAutoByName) ? 'auto' : 'manual');
            loadedBookmarks++;
          }
        });
      }
      // First load without explicit bookmarks: auto-generate from chapter folders.
      if(!hadBookmarksBefore && loadedBookmarks===0){
        _convBuildAutoFolderBookmarks(files,path).forEach(bm=>{
          _convSetBookmarkWithOrigin(bm.relPath,bm.name,path,'auto');
        });
      }
      // Backfill missing bookmark origin (for old sidecars/localStorage created before origin tracking).
      files.forEach(f=>{
        const rp=_convNormPath(f.relPath);
        const name=(S.convBookmarks[rp]||'').trim();
        if(!rp||!name||_convBookmarkOriginExists(rp)) return;
        const folder=f.folder||'';
        const guessed=(convGuessChapterName(folder)||'').trim();
        const isFirstInFolder=firstRelByFolder[folder]===rp;
        const isAuto=!!guessed && guessed===name && isFirstInFolder;
        S.convBookmarkOrigin[rp]=isAuto?'auto':'manual';
      });
      render();
      return true;
    }
  }catch(e){
    console.error(e);
    if(_convSourceLoads.get(path)===pending&&S.convSources.includes(path)){
      (S._convSourceErrors||(S._convSourceErrors={}))[path]=String(e.message||e);
      render();
    }
  }
  return false;
}
// A spread is cut in two, and the automatic crop chases the ink of each half on
// its own -- the halves come back trimmed differently and stop meeting at the
// seam. So every wide page is marked No Crop the first time its source opens.
// The sidecar remembers which pages that was done for, so one taken off by hand
// is never put back.
async function _convDetectSpreads(source,isCurrent=()=>S.convSources.includes(source)){
  if(!source||!isCurrent())return false;
  try{
    const r=await(await apiPost('/api/convert/detect-spreads',{path:source})).json();
    if(!r||!r.ok||!isCurrent())return false;
    const owned=S._convAutoNoCrop||(S._convAutoNoCrop={});
    (Array.isArray(r.spreads)?r.spreads:[]).forEach(rel=>{const rp=_convNormPath(rel);if(rp)owned[rp]=source;});
    let changed=false;
    (Array.isArray(r.applied)?r.applied:[]).forEach(rel=>{
      const rp=_convNormPath(rel);
      if(!rp||S.convExclusions[rp])return;
      _convToggleNoCrop(rp,true);
      changed=true;
    });
    if(changed)render();
    return true;
  }catch(e){console.error(e);}
  return false;
}
// Write one source's whole per-page state back to its sidecar. Every key goes
// along: the endpoint replaces what it is given and drops what it is not.
async function _convSaveSidecarForSource(src){
  const files=S.convScanned[src]||[];
  if(!files.length)return false;
  const relPaths=new Set(files.map(f=>f.relPath));
  const normRelPaths=new Set(files.map(f=>_convNormPath(f.relPath)));
  const nc=Object.entries(S.convExclusions).filter(([k,v])=>v['no-crop']&&relPaths.has(k)).map(([k])=>k);
  const cc={};Object.entries(S.convCustomCrop).forEach(([k,v])=>{if(relPaths.has(k))cc[k]=v;});
  const cs={};Object.entries(S.convCustomSplit).forEach(([k,v])=>{if(relPaths.has(k))cs[k]=v;});
  const ex=Object.keys(S.convExcluded).filter(k=>relPaths.has(k));
  const em={};Object.entries(S.convExtraMargin).forEach(([k,v])=>{if(relPaths.has(k))em[k]={...v,color:v.color||S._convExtraMarginColor};});
  const eo={};Object.entries(S.convEditOps).forEach(([k,v])=>{if(relPaths.has(k)&&v&&v.length)eo[k]=v;});
  const bms=Object.entries(S.convBookmarks||{}).filter(([k,name])=>relPaths.has(k)&&String(name||'').trim()).map(([relPath,name])=>({relPath,name}));
  const wm=_convWatermarkMatchList(src).filter(rel=>normRelPaths.has(_convNormPath(rel)));
  try{
    const saved={source:src,'no-crop':nc,'custom-crop':cc,'custom-split':cs,'excluded':ex,'bookmarks':bms,'extra-margin':em,'edit-ops':eo};
    if(_convIsWatermarkReviewed(src))saved['watermark-matches']=wm;
    const response=await apiPost('/api/crop-sidecar/save',saved);
    const result=await response.json();
    if(!response.ok||!result.ok)throw new Error(result.error||'Sidecar save failed');
    sessionStorage.setItem('mcs_convWatermarkReviewed',JSON.stringify(S.convWatermarkReviewed));
    return true;
  }catch(e){
    console.error(e);
    S.status='⚠ '+String(e&&e.message||e);
    render();
    return false;
  }
}
function _resetCropData(){S.convExclusions={};S.convCustomCrop={};S.convCustomSplit={};S.convExcluded={};S.convExtraMargin={};S.convEditOps={};S.convWatermarkMatches={};S.convWatermarkReviewed={};_invalidateCropCaches();
  sessionStorage.removeItem('mcs_convExclusions');sessionStorage.removeItem('mcs_convExcluded');sessionStorage.removeItem('mcs_convCustomCrop');sessionStorage.removeItem('mcs_convCustomSplit');sessionStorage.removeItem('mcs_convExtraMargin');sessionStorage.removeItem('mcs_convEditOps');sessionStorage.removeItem('mcs_convWatermarkMatches');sessionStorage.removeItem('mcs_convWatermarkReviewed');}
function _convClearEditCropForRel(relPath){
  const rp=_convNormPath(relPath);
  if(!rp)return;
  const key=String(S._editCropKey||'');
  if(key&&key.includes('|'+rp+'|')){
    S._editCrop=null;
    S._editCropKey='';
  }
}
function _convToggleNoCrop(relPath,forceEnable){
  const rp=_convNormPath(relPath);
  if(!rp)return;
  const cur=!!(S.convExclusions[rp]&&S.convExclusions[rp]['no-crop']);
  const next=(typeof forceEnable==='boolean')?forceEnable:!cur;
  if(next){
    S.convExclusions[rp]={'no-crop':true};
    if(S.convCustomCrop[rp])delete S.convCustomCrop[rp];
    if(S.convCustomSplit[rp])delete S.convCustomSplit[rp];
    _convClearEditCropForRel(rp);
  } else {
    delete S.convExclusions[rp];
    if(S.convCustomSplit[rp])delete S.convCustomSplit[rp];
    // The spread scan put this mark here, so taking it off has to reach the
    // sidecar now -- that is where the scan reads that it must not come back.
    const owner=S._convAutoNoCrop&&S._convAutoNoCrop[rp];
    if(owner)_convSaveSidecarForSource(owner);
  }
  _invalidateCropCaches();
}
// The formats whose pages a Kindle eventually judges by the pixels along a
// split spread: KFX directly, EPUB after Send-to-Kindle converts it to KFX.
function _seamFormat(fmt){const f=(fmt||'').toUpperCase();return f==='KFX MAIC'||f==='KFX + MOBI MAIC'||f==='EPUB MAIC';}
function _isNativeFormat(fmt){const f=(fmt||'').toUpperCase();return f==='KFX MAIC'||f==='KFX + MOBI MAIC'||f==='MOBI MAIC'||f==='EPUB MAIC';}
// Preserve saved KCC settings, but never send them with a native job. In
// particular webtoon/batch_split/chunk_size would force a fallback to KCC.
function _convEffectivePayload(body){
  if(!_isNativeFormat(body.format))return body;
  return {...body,webtoon:false,batch_split:0,chunk_size:0,splitter:0,
    upscale:false,stretch:false,hq:body.format.toUpperCase().startsWith('KFX')?false:!!body.hq,autoscale:false,
    gamma:0,cropping:0,cropping_power:1,preserve_margin_h:0,preserve_margin_v:0,
    auto_balance_margins:false,auto_balance_margin_px:0,auto_balance_margin_pct:0,
    auto_balance_margin_unit:'px',no_autocontrast:false,color_autocontrast:false,
    autolevel:0,erase_rainbow:false,spread_shift:false,match_spread_width:false,
    screen_margins:false,metadata_title:0,delete_input:false,file_fusion:false,
    rotate_first:false,pdf_legacy:false,inter_panel_crop:0,
    mozjpeg:body.format.toUpperCase().startsWith('KFX')?false:body.mozjpeg};
}
function _convDisableControl(el,tip){
  el.querySelectorAll('input,select,button,textarea').forEach(input=>{input.disabled=true;});
  el.setAttribute('aria-disabled','true');
  el.style.opacity='0.45';
  // Keep pointer events on the label so its explanation remains available.
  el.style.cursor='not-allowed';
  if(tip)el.setAttribute('data-tip',tip);
  return el;
}
// The splitter tri-state is KCC's. The three "maic" formats split by ratio in
// their own pipeline, and plain KFX hands whole spreads to Previewer, so for
// both the setting reads as Off wherever it is consulted -- which is what the
// disabled control already shows.
function _convEffectiveSplitter(){
  const fmt=(S.convFormat||'').toUpperCase();
  if(fmt.startsWith('KFX')||_isNativeFormat(S.convFormat))return 0;
  return parseInt(S.convSplitter,10)||0;
}
async function startConversion(){
  if(S._convStarting||S.convStatus.converting||S.convSources.length===0)return;
  S._convStarting=true;
  render();
  try{
    // Even a collapsed source must have all saved page rules loaded before
    // building payloads or writing sidecars. Preparation runs once, on demand.
    const sources=[...S.convSources];
    for(const source of sources){
      if((S._convSourceErrors||{})[source])_convForgetSource(source);
      if(!await _convPrepareSource(source))throw new Error(
        t('conv.source_prepare_failed','Could not prepare source: {source}').replace('{source}',source));
      if(S.convMaicWatermarks&&!await _convAutoScanWatermarks([source]))throw new Error(
        t('conv.source_prepare_failed','Could not prepare source: {source}').replace('{source}',source));
    }
    if(sources.length!==S.convSources.length||sources.some((src,i)=>src!==S.convSources[i]))return;
    await _convStartPreparedConversion(sources);
  }catch(e){alert(e.message);}
  finally{S._convStarting=false;render();}
}
async function _convStartPreparedConversion(sources=[...S.convSources]){
  // Reset view & status
  S.convViewIdx=null;convResetView();
  S.convStatus={converting:false,progress:0,output_files:[],log:[]};
  render();
  // Step 1: Save crop data for each source
  const allExcl=Object.entries(S.convExclusions).filter(([k,v])=>v['no-crop']);
  const allCC=Object.entries(S.convCustomCrop);
  const allCS=Object.entries(S.convCustomSplit);
  const allEM=Object.entries(S.convExtraMargin);
  const allEO=Object.entries(S.convEditOps);
  for(const src of sources){
    const files=S.convScanned[src]||[];
    const relPaths=new Set(files.map(f=>f.relPath));
    const normRelPaths=new Set(files.map(f=>_convNormPath(f.relPath)));
    const nc=allExcl.filter(([k])=>relPaths.has(k)).map(([k])=>k);
    const cc={};allCC.forEach(([k,v])=>{if(relPaths.has(k))cc[k]=v;});
    const splits={};allCS.forEach(([k,v])=>{if(relPaths.has(k))splits[k]=v;});
    const em={};allEM.forEach(([k,v])=>{if(relPaths.has(k))em[k]={...v,color:v.color||S._convExtraMarginColor};});
    const eo={};allEO.forEach(([k,v])=>{if(relPaths.has(k)&&v&&v.length)eo[k]=v;});
    const ex2=Object.keys(S.convExcluded).filter(k=>relPaths.has(k));
    const bms=Object.entries(S.convBookmarks||{}).filter(([k,name])=>relPaths.has(k)&&String(name||'').trim()).map(([relPath,name])=>({relPath,name}));
    const wm=_convWatermarkMatchList(src).filter(rel=>normRelPaths.has(_convNormPath(rel)));
    if(nc.length||Object.keys(cc).length||Object.keys(splits).length||ex2.length||bms.length||Object.keys(em).length||Object.keys(eo).length||wm.length||_convIsWatermarkReviewed(src)){
      const saved={source:src,'no-crop':nc,'custom-crop':cc,'custom-split':splits,'excluded':ex2,'bookmarks':bms,'extra-margin':em,'edit-ops':eo};
      if(_convIsWatermarkReviewed(src))saved['watermark-matches']=wm;
      const response=await apiPost('/api/crop-sidecar/save',saved);
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'Sidecar save failed');
    }
  }
  // Step 2: Build per-source crop data
  // Resolve real KCC profile key (entry_key -> profile_key)
  let _kccProfileKey = S.convProfile;
  if(S.convProfiles){
    Object.values(S.convProfiles).forEach(g=>{
      if(g[S.convProfile]) _kccProfileKey = g[S.convProfile].profile_key || S.convProfile;
    });
  }
  const perSourceCrop={};
  for(const src of sources){
    const files=S.convScanned[src]||[];
    const relPaths=new Set(files.map(f=>f.relPath));
    const nc=allExcl.filter(([k])=>relPaths.has(k)).map(([k])=>k);
    const cc={};allCC.forEach(([k,v])=>{if(relPaths.has(k))cc[k]=v;});
    if(nc.length||Object.keys(cc).length) perSourceCrop[src]={'no-crop':nc,'custom-crop':cc};
  }
  // Step 3: Start conversion
  const body={
    sources, profile:_kccProfileKey, format:S.convFormat,
    output_dir:S.convOutputDir, title:S.convTitle, author:S.convAuthor,
    manga_mode:S.convManga, grayscale:S.convGrayscale, cropping:S.convCropping,
    maic_crop:!!S.convMaicCrop,
    maic_margin_pct:Math.max(0,Math.min(10,parseFloat(S.convMaicMarginPct)||0)),
    maic_watermarks:!!S.convMaicWatermarks,
    maic_page_numbers:!!S.convMaicPageNumbers,
    manga_upscale:_isNativeFormat(S.convFormat)?(parseInt(S.convMangaUpscale)||0):0,
    scan_cleanup:_isNativeFormat(S.convFormat)?!!S.convScanCleanup:false,
    facing_pages:_isNativeFormat(S.convFormat)?!!S.convFacingPages:false,
    spread_preview_mode:_seamFormat(S.convFormat)?(parseInt(S.convSpreadPreviewMode)||0):0,
    // Kept for an older backend/preset; the explicit tri-state above wins.
    force_spread_preview:_seamFormat(S.convFormat)&&(parseInt(S.convSpreadPreviewMode)||0)===2,
    cleanup_method:S.cleanMethod||'lama',
    cleanup_padding:parseInt(S.maskPadding)||0,
    cropping_power:parseFloat(S.convCroppingPower)||1.0,
    preserve_margin_h:parseInt(S.convPreserveMarginH)||0,
    preserve_margin_v:parseInt(S.convPreserveMarginV)||0,
    splitter:_convEffectiveSplitter(), upscale:_isNativeFormat(S.convFormat)?false:S.convUpscale===2, stretch:_isNativeFormat(S.convFormat)?false:S.convUpscale===1,
    hq:(S.convFormat||'').toUpperCase().startsWith('KFX')?false:S.convHQ===2,
    autoscale:(S.convFormat||'').toUpperCase().startsWith('KFX')?false:S.convHQ===1,
    webtoon:S.convWebtoon,
    no_rotate:S.convNoRotate, rotate_first:S.convRotateFirst,
    auto_balance_margins:(parseInt(S.convAutoBalanceMode)||0)===1,
    auto_balance_margin_unit:(parseInt(S.convAutoBalanceMode)||0)===1?((S.convAutoBalanceMarginUnit||'px')==='pct'?'pct':'px'):'px',
    auto_balance_margin_px:(parseInt(S.convAutoBalanceMode)||0)===1&&((S.convAutoBalanceMarginUnit||'px')!=='pct')?(parseInt(S.convAutoBalanceMarginPx)||0):0,
    auto_balance_margin_pct:(parseInt(S.convAutoBalanceMode)||0)===1&&((S.convAutoBalanceMarginUnit||'px')==='pct')?(parseFloat(S.convAutoBalanceMarginPct)||0):0,
    kindle_doc_type:S.convKindleDocType==='pdoc'?'pdoc':'ebok',
    gamma:parseFloat(S.convGamma)||0, no_autocontrast:S.convNoAutocontrast,
    color_autocontrast:S.convColorAutocontrast, autolevel:S.convAutolevel,
    borders_color:S.convBordersColor, force_color:S.convForceColor,
    force_png:S.convForcePNG===1, mozjpeg:S.convForcePNG===2,
    inter_panel_crop:S.convInterPanelCrop, erase_rainbow:S.convEraseRainbow,
    spread_shift:S.convSpreadShift, match_spread_width:S.convMatchSpreadWidth,
    screen_margins:S.convScreenMargins, delete_input:S.convDeleteInput,
    kfx_no_padding:S.convKfxNoPadding,
    no_processing:S.convNoProcessing, batch_split:S.convBatchSplit,
    file_fusion:S.convFileFusion,
    metadata_title:S.convMetadataTitle||0,
    vol_prefix:S.convVolPrefix||'Vol.',
    custom_width:parseInt(S.convCustomW)||0, custom_height:parseInt(S.convCustomH)||0,
    jpeg_quality:S.convCustomJpeg?(parseInt(S.convJpegQ)||85):85,
    chunk_size:S.convChunkSize, pdf_legacy:S.convPdfLegacy,
    per_source_crop:perSourceCrop,
    excluded_files:Object.keys(S.convExcluded),
    bookmarks:S.convBookmarks||{},
  };
  try{
    try{await apiPost('/api/convert/log-mode',{advanced:!!S.convAdvancedLog});}catch(e){}
    if(sources.length!==S.convSources.length||sources.some((src,i)=>src!==S.convSources[i]))return;
    const r=await(await apiPost('/api/convert/start',_convEffectivePayload(body))).json();
    if(r.ok){
      if(S.convPollId){clearTimeout(S.convPollId);S.convPollId=null;}
      S.convStatus.converting=true;
      render();
      _scheduleConvertPoll(250);
    }
    else alert(r.error);
  }catch(e){alert(e.message);}
}

function renderConvert(app){
  loadConvertProfiles();
  const cs=S.convStatus;
  const _cropFeatureEnabled=(S.convCropping>0||S.convMaicCrop||S.convInterPanelCrop>0);
  const _CONV_CANVAS_MIN_W_PX=760;
  const body=h('div',{className:'body'});
  body.style.overflowX='auto';
  body.style.overflowY='hidden';

  // Encoding-normalized comment.
  const sb=h('div',{className:'sidebar convert-sidebar'});
  const sbh=h('div',{className:'sidebar-hdr conv-sidebar-hdr'+(S.convSources.length>1?' many-sources':' single-source')});

  // Total file count across all sources
  const totalFiles=S.convSources.reduce((count,source)=>count+(S.convScanned[source]||[]).length,0);

  if(S.convSources.length>0){
    // Title row with count + add + close
    const titleRow=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'0.5rem'}});
    const titleLeft=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem'}});
    titleLeft.append(h('span',{style:{fontSize:'0.75rem',fontWeight:'600',color:'var(--text)'}},t('files')));
    titleLeft.append(h('span',{style:{fontSize:'0.65rem',fontWeight:'600',color:'var(--accent)',background:'rgba(110,170,255,0.12)',
      padding:'0.1rem 0.4rem',borderRadius:'10px'}},String(totalFiles||S.convSources.length)));
    titleRow.append(titleLeft);
    const titleBtns=h('div',{style:{display:'flex',gap:'0.3rem'}});
    titleBtns.append(h('button',{style:{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',color:'var(--text2)',fontSize:'0.7rem',transition:'all .2s'},
      onClick:showSourceModal,title:t('files.add_source')},'+'));
    titleBtns.append(h('button',{style:{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'50%',
      width:'1.4rem',height:'1.4rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',color:'var(--text3)',transition:'all .2s'},
      onClick:()=>{S.convSources.forEach(_convForgetSource);S.convSources=[];S.convScanned={};S.convCollapsed={};S.convExpandedSource=null;_resetCropData();S.convBookmarks={};S.convBookmarkOrigin={};S.convAutoBmSuppressed={};render();},
      onMouseover:function(){this.style.color='var(--red)';this.style.borderColor='rgba(248,113,113,0.3)';},
      onMouseout:function(){this.style.color='var(--text3)';this.style.borderColor='var(--glass-border)';},
      title:t('files.clear_all'),innerHTML:'<svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'}));
    titleRow.append(titleBtns);
    sbh.append(titleRow);

    // Source paths as pills (like clean tab)
    const srcList=h('div',{className:'conv-source-list'});
    S.convSources.forEach((s,i)=>{
      const name=s.split(/[/\\]/).filter(Boolean).slice(-2).join('/');
      const isDir=!s.match(/\.\w{2,4}$/);
      const pill=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.3rem 0.5rem',
        background:'var(--glass2)',borderRadius:'var(--radius-xs)',border:'1px solid var(--glass-border)',marginBottom:'0.25rem',cursor:'pointer',transition:'all .2s'},
        title:s,onClick:()=>{S.convViewIdx=null;const open=!_convSourceIsOpen(s);S.convCollapsed['src:'+i]=!open;S.convExpandedSource=open?s:null;if(open)_convPrepareSource(s);render();},
        onMouseover:function(){this.style.borderColor='rgba(110,170,255,0.3)';},
        onMouseout:function(){this.style.borderColor='var(--glass-border)';}});
      pill.append(h('span',{innerHTML:isDir?'<svg width="12" height="12" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>':'<svg width="12" height="12" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6M9 13h4"/></svg>'}));
      pill.append(h('span',{style:{fontSize:'0.68rem',color:'var(--text2)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:'1'}},name));
      const scanned=S.convScanned[s];
      if(scanned)pill.append(h('span',{style:{fontSize:'0.55rem',color:'var(--text3)'}},scanned.length+''));
      pill.append(h('span',{style:{fontSize:'0.55rem',color:'var(--text3)',cursor:'pointer',padding:'0 0.1rem'},
        onClick:e=>{e.stopPropagation();
          // Remove crop data only for this source's files
          const removedFiles=S.convScanned[s]||[];
          removedFiles.forEach(f=>{if(f.relPath){delete S.convExclusions[f.relPath];delete S.convCustomCrop[f.relPath];delete S.convCustomSplit[f.relPath];delete S.convExcluded[f.relPath];delete S.convBookmarks[f.relPath];delete S.convBookmarkOrigin[f.relPath];}});
          _convForgetSource(s);
          S.convSources.splice(i,1);delete S.convScanned[s];
          delete S.convWatermarkMatches[s];delete S.convWatermarkReviewed[s];
          const collapsed={};
          Object.entries(S.convCollapsed).forEach(([key,value])=>{
            const match=key.match(/^(src|f):(\d+)(:.*)?$/);
            if(!match){collapsed[key]=value;return;}
            const index=Number(match[2]);
            if(index!==i)collapsed[match[1]+':'+(index>i?index-1:index)+(match[3]||'')]=value;
          });
          S.convCollapsed=collapsed;
          if(S.convExpandedSource===s)S.convExpandedSource=null;
          _invalidateCropCaches();render();},
        onMouseover:function(){this.style.color='var(--red)';},
        onMouseout:function(){this.style.color='var(--text3)';}},'\u2715'));
      srcList.append(pill);
    });
    sbh.append(srcList);

    // Output dir pill
    const outName=S.convOutputDir?S.convOutputDir.split(/[/\\]/).filter(Boolean).slice(-2).join('/'):t('export.next_to_source');
    const outPill=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.3rem 0.5rem',
      background:'rgba(52,211,153,0.06)',borderRadius:'var(--radius-xs)',border:'1px solid rgba(52,211,153,0.15)',cursor:'pointer',transition:'all .2s'},
      onClick:selectConvertOutput,title:t('export.save_folder')});
    outPill.append(h('span',{innerHTML:'<svg width="12" height="12" fill="none" stroke="#34d399" stroke-width="1.8" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>'}));
    outPill.append(h('span',{style:{fontSize:'0.68rem',color:'var(--green)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:'1',opacity:S.convOutputDir?1:0.5}},outName));
    outPill.append(h('span',{style:{fontSize:'0.6rem',color:'var(--text3)',flexShrink:'0'}},'\u270e'));
    sbh.append(outPill);
    sb.append(sbh);
  }

  // Source tree or dropzone
  if(S.convSources.length===0){
    const dz=h('button',{className:'sidebar-dropzone',onClick:showSourceModal});
    dz.innerHTML='<svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24" style="color:var(--text3);margin-bottom:0.6rem"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z" stroke-linecap="round"/><path d="M12 10v6M9 13h6" stroke-linecap="round"/></svg>';
    dz.append(h('div',{style:{fontSize:'0.78rem',color:'var(--text2)',fontWeight:'500'}},t('files.add_source')));
    dz.append(h('div',{style:{fontSize:'0.65rem',color:'var(--text3)',marginTop:'0.3rem'}},t('files.folder_or_archive')));
    sb.append(dz);
  } else {
    const tree=h('div',{className:'file-tree'});
    S.convSources.forEach((src,si)=>{
      const srcName=src.split(/[/\\]/).filter(Boolean).slice(-1)[0];
      const srcKey='src:'+si;
      const srcOpen=_convSourceIsOpen(src);
      const scanned=S.convScanned[src];
      const srcCount=scanned?scanned.length:0;
      const sourceError=(S._convSourceErrors||{})[src];
      if(!scanned&&!sourceError)scanConvertSource(src);
      if(srcOpen&&!sourceError)_convPrepareSource(src);

      // Source header (collapsible)
      const srcHdr=h('div',{className:'group-header','data-key':srcKey,style:{cursor:'pointer',fontWeight:'600'},
        onClick:()=>{
          const ft=document.querySelector('.file-tree');
          if(ft)S._convScrollTop=ft.scrollTop;
          S._convScrollToKey=srcKey;
          S.convCollapsed[srcKey]=srcOpen;
          if(!srcOpen)_convPrepareSource(src);
          if(!srcOpen)S.convExpandedSource=src;
          render();
        }});
      srcHdr.append(h('span',{className:'g-icon',style:{fontSize:'0.6rem',transition:'transform .15s',
        transform:srcOpen?'rotate(90deg)':'rotate(0deg)'}},'\u25B6'));
      srcHdr.append(h('span',{style:{fontSize:'0.8rem'}},src.match(/\.\w{2,4}$/)?'\ud83d\udce6':'\ud83d\udcc1'));
      srcHdr.append(h('span',{style:{flex:'1',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},srcName));
      if(srcCount)srcHdr.append(h('span',{className:'group-count'},'('+srcCount+')'));
      if(!scanned&&!sourceError)srcHdr.append(h('span',{className:'group-count'},t('clean.loading')));
      tree.append(srcHdr);
      if(sourceError){
        tree.append(h('button',{title:sourceError,onClick:()=>{
          _convForgetSource(src);scanConvertSource(src);
          if(srcOpen)_convPrepareSource(src);render();
        }},t('conv.source_retry','Retry loading source')));
      }

      // Source contents (when open)
      if(srcOpen){
        if(!scanned){
          tree.append(h('div',{style:{padding:'0.4rem 1.2rem',fontSize:'0.65rem',color:'var(--text3)',fontStyle:'italic'}},t('clean.loading')));
        } else if(scanned.length===0){
          tree.append(h('div',{style:{padding:'0.4rem 1.2rem',fontSize:'0.65rem',color:'var(--text3)'}},t('clean.no_images')));
        } else {
          // Group by folder
          const groups={};
          scanned.forEach(f=>{const g=f.folder||'';if(!groups[g])groups[g]=[];groups[g].push(f);});
          // Encoding-normalized comment.
          const multiGroup=Object.keys(groups).some(k=>k!=='');

          Object.entries(groups).forEach(([folder,gFiles])=>{
            const fKey='f:'+si+':'+folder;
            const fOpen=!S.convCollapsed[fKey];

            if(multiGroup&&folder!==''){
              // Encoding-normalized comment.
              const fHdr=h('div',{className:'group-header','data-key':fKey,style:{cursor:'pointer',paddingLeft:'1rem'},
                onClick:()=>{
                  const ft=document.querySelector('.file-tree');
                  if(ft)S._convScrollTop=ft.scrollTop;
                  S._convScrollToKey=fKey;
                  S.convCollapsed[fKey]=fOpen;render();
                }});
              fHdr.append(h('span',{className:'g-icon',style:{fontSize:'0.55rem',transition:'transform .15s',
                transform:fOpen?'rotate(90deg)':'rotate(0deg)'}},'\u25B6'));
              const isArchGroup=gFiles.length>0&&gFiles[0].archive;
              fHdr.append(h('span',{style:{fontSize:'0.8rem'}},isArchGroup?'\ud83d\udce6':'\ud83d\udcc1'));
              fHdr.append(h('span',{style:{flex:'1',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},folder));
              fHdr.append(h('span',{className:'group-count'},'('+gFiles.length+')'));
              tree.append(fHdr);
            }

            if(!multiGroup||fOpen){
              gFiles.forEach(f=>{
                const globalIdx=scanned.indexOf(f);
                const thumbUrl=API+'/api/convert/serve-thumb?path='+encodeURIComponent(f.path);
                const isNoCrop=!!(S.convExclusions[f.relPath]&&S.convExclusions[f.relPath]['no-crop']);
                const isCustomCrop=!!S.convCustomCrop[f.relPath];
                const isExcluded=!!S.convExcluded[f.relPath];
                const watermarkCount=S.convMaicWatermarks
                  ?Math.max(0,Number((((S.convWatermarkMatches||{})[src]||{})[_convNormPath(f.relPath)])||0)):0;
                const isViewing=(S.convExpandedSource===src&&S.convViewIdx===globalIdx);
                const _isWideThumb=!!(S._wideThumbByPath&&S._wideThumbByPath[f.path]);
                const itemStyle=Object.assign({},(multiGroup&&folder!=='')?{paddingLeft:'1.5rem'}:{},
                  isExcluded?{borderColor:'rgba(248,113,113,0.3)',background:'rgba(248,113,113,0.04)',opacity:'0.5'}:
                  isNoCrop?{borderColor:'rgba(251,146,60,0.3)',background:'rgba(251,146,60,0.06)'}:
                  isCustomCrop?{borderColor:'rgba(110,170,255,0.3)',background:'rgba(110,170,255,0.06)'}:{});
                const item=h('div',{className:'file-item'+(isViewing?' active':'')+(_isWideThumb?' wide':''),style:itemStyle,
                  onClick:()=>{
                    convResetView();S.convExpandedSource=src;S.convViewIdx=globalIdx;_convSetSplitStep(f.relPath,0);render();
                  },
                  onContextmenu:e=>{
                    e.preventDefault();
                    if(e.altKey){
                      if(S.convExcluded[f.relPath]){delete S.convExcluded[f.relPath];}
                      else{S.convExcluded[f.relPath]=true;}
                    } else {
                      if(!_cropFeatureEnabled)return;
                      _convToggleNoCrop(f.relPath);
                    }
                    render();
                  }});
                item.append(h('img',{className:'file-thumb',src:thumbUrl,loading:'lazy',
                  onLoad:function(){
                    const isWide=_isWideSidebarThumb(this.naturalWidth,this.naturalHeight);
                    if(!S._wideThumbByPath)S._wideThumbByPath={};
                    S._wideThumbByPath[f.path]=isWide;
                    const p=this.parentElement;
                    if(p)p.classList.toggle('wide',isWide);
                  }}));
                const info=h('div',{className:'file-info'});
                info.append(h('div',{className:'file-name'},f.name));
                if(isExcluded){info.append(h('div',{style:{fontSize:'0.6rem',color:'var(--red)',fontWeight:'500',marginTop:'1px'}},'\u2715 Excluded'));}
                else if(isNoCrop){info.append(h('div',{style:{fontSize:'0.6rem',color:'var(--orange)',fontWeight:'500',marginTop:'1px'}},'\u2298 No Crop'));}
                else if(isCustomCrop){info.append(h('div',{style:{fontSize:'0.6rem',color:'var(--accent)',fontWeight:'500',marginTop:'1px'}},'\u2702 Custom Crop'));}
                if(watermarkCount){
                  info.append(h('div',{title:t('conv.watermark_badge_tip','A trained watermark was detected on this page.'),style:{
                    display:'inline-flex',alignItems:'center',alignSelf:'flex-start',fontSize:'0.58rem',lineHeight:'1',
                    color:'#facc15',fontWeight:'650',marginTop:'3px',padding:'0.14rem 0.34rem',borderRadius:'999px',
                    background:'rgba(234,179,8,0.14)',border:'1px solid rgba(250,204,21,0.38)'
                  }},'\u25C7 '+t('conv.watermark_badge','Watermark')));
                }
                const _isExtraMargin=!!(S.convExtraMargin[f.relPath]&&(S.convExtraMargin[f.relPath].top||S.convExtraMargin[f.relPath].bottom||S.convExtraMargin[f.relPath].left||S.convExtraMargin[f.relPath].right));
                if(_isExtraMargin){info.append(h('div',{style:{fontSize:'0.6rem',color:'rgb(34,197,94)',fontWeight:'500',marginTop:'1px'}},'+ Margin'));}
                const _hasEditOps=!!(S.convEditOps[f.relPath]&&S.convEditOps[f.relPath].length);
                if(_hasEditOps){info.append(h('div',{style:{fontSize:'0.6rem',color:'var(--orange)',fontWeight:'500',marginTop:'1px'}},'\u270E Edit'));}
                const pageNumbers=S.convMaicPageNumbers&&((S.convPageNumberMatches||{})[f.path]||[])
                  .filter(text=>Number(text)>=_convPageNumberMinimum(f,src));
                info.append(h('div',{className:'conv-page-number-badge',
                  'data-page-number-scope':src,'data-page-number-path':f.path,hidden:!pageNumbers||!pageNumbers.length,
                  style:{fontSize:'0.6rem',color:'var(--accent)',fontWeight:'500',marginTop:'1px'}},
                  pageNumbers&&pageNumbers.length?'\u2460 num '+pageNumbers.join(', '):''));
                if(S.convBookmarks[f.relPath]){
                  const _bmOrigin=_convBookmarkOriginOf(f.relPath);
                  const _isAuto=_bmOrigin==='auto';
                  const bmRow=h('div',{style:{display:'flex',alignItems:'center',gap:'0.25rem',fontSize:'0.6rem',marginTop:'1px',maxWidth:'8rem',minWidth:0}});
                  if(_isAuto){
                    bmRow.append(h('span',{style:{
                      fontSize:'0.5rem',
                      color:'#34d399',
                      background:'rgba(52,211,153,0.14)',
                      border:'1px solid rgba(52,211,153,0.35)',
                      borderRadius:'999px',
                      padding:'0.02rem 0.28rem',
                      flexShrink:0
                    }},'AUTO'));
                  }
                  bmRow.append(h('span',{style:{color:'var(--accent)',fontWeight:'500',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',minWidth:0}},'\u2691 '+S.convBookmarks[f.relPath]));
                  info.append(bmRow);
                }
                item.append(info);
                tree.append(item);
              });
            }
          });
        }
      }
    });
    sb.append(tree);
  }

  // Sidebar footer: convert button
  const sbFooter=h('div',{style:{padding:'0.5rem',borderTop:'1px solid var(--glass-border)',flexShrink:0}});
  if(!cs.converting){
    const goBtn=h('button',{id:'convGoBtn',style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      width:'100%',padding:'0.55rem',borderRadius:'var(--radius-xs)',fontSize:'0.78rem',fontWeight:'600',
      cursor:S._convStarting?'wait':'pointer',transition:'all .2s',
      background:'var(--green-bg)',border:'1px solid var(--green-border)',color:'var(--green)',
      opacity:S.convSources.length===0?'0.4':'1'},
      disabled:!!S._convStarting,
      onClick:()=>{if(S.convSources.length>0)startConversion();},
      onMouseover:function(){if(S.convSources.length>0)this.style.background='rgba(74,222,128,0.2)';},
      onMouseout:function(){this.style.background='var(--green-bg)';}});
    goBtn.append(S._convStarting?t('conv.preparing_sources','Preparing sources…'):t('conv.convert','Convert'));
    sbFooter.append(goBtn);
  } else {
    const stopBtn=h('button',{id:'convGoBtn',style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      width:'100%',padding:'0.55rem',borderRadius:'var(--radius-xs)',fontSize:'0.78rem',fontWeight:'600',
      cursor:'pointer',transition:'all .2s',
      background:'var(--red-bg)',border:'1px solid rgba(248,113,113,0.2)',color:'var(--red)'},
      onClick:()=>apiPost('/api/convert/stop',{})});
    stopBtn.append(t('conv.stop','Stop'));
    sbFooter.append(stopBtn);
  }
  sb.append(sbFooter);

  body.append(sb);
  requestAnimationFrame(()=>{
    if(sb.isConnected)setupConvertDragDrop(sb);
  });

  // Encoding-normalized comment.
  const main=h('div',{className:'main',style:{minWidth:(_CONV_CANVAS_MIN_W_PX+20)+'px'}});

  // Get current viewing file (needed for toolbar)
  const _cvScanned=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
  const _cvFile=(_cvScanned&&S.convViewIdx!==null&&S.convViewIdx>=0)?_cvScanned[S.convViewIdx]:null;
  const _cvRel=_cvFile?_convNormPath(_cvFile.relPath):'';
  const _cropEnabled=_cvFile&&_cropFeatureEnabled;
  const _isNoCrop=!!(_cvFile&&S.convExclusions[_cvFile.relPath]&&S.convExclusions[_cvFile.relPath]['no-crop']);
  const _isExcludedCanvas=!!(_cvFile&&S.convExcluded[_cvFile.relPath]);
  const _previewReqBase=_cvFile?_convBuildPreviewRequest(_cvFile):null;
  const _previewKeyBase=_previewReqBase?_convPreviewCacheKey(_previewReqBase):'';
  const _previewMetaBase=(_previewKeyBase&&S._cropCache&&S._cropCache.key===_previewKeyBase)?S._cropCache.data:null;
  const _splitterMode=_convEffectiveSplitter();
  const _splitPairMode=_splitterMode!==1;
  const _selVariant=String(S.convPreviewVariant||'auto').toUpperCase();
  let _halfOrder=_splitPairMode?_convExtractHalfOrder((_previewMetaBase&&Array.isArray(_previewMetaBase.output_variants))?_previewMetaBase.output_variants:[]):[];
  if(!_halfOrder.length&&_cvFile&&_splitPairMode)_halfOrder=_convGetSplitOrderForFile(_cvFile);
  let _stepMode=!!(_cvFile&&_splitPairMode&&_selVariant==='AUTO'&&_halfOrder.length>1);
  let _splitStep=_stepMode?_convGetSplitStep(_cvRel,_halfOrder.length):0;
  let _activeVariant=_stepMode?_halfOrder[_splitStep]:null;
  if(_stepMode)_convSetSplitStep(_cvRel,_splitStep);
  let _previewReq=_previewReqBase?{..._previewReqBase,preview_variant:_activeVariant||_previewReqBase.preview_variant}:null;
  let _previewKey=_previewReq?_convPreviewCacheKey(_previewReq):'';
  const _previewMetaEff=(_previewKey&&S._cropCache&&S._cropCache.key===_previewKey)?S._cropCache.data:null;
  const _previewMeta=_previewMetaBase||_previewMetaEff;
  const _previewModes=(_previewMeta&&Array.isArray(_previewMeta.output_variants))?_previewMeta.output_variants:[];
  const _metaHalfOrder=_convExtractHalfOrder(_previewModes);
  if(_splitPairMode&&_metaHalfOrder.length){
    const _prevKey=_halfOrder.join('|');
    const _nextKey=_metaHalfOrder.join('|');
    if(_prevKey!==_nextKey){
      _halfOrder=_metaHalfOrder;
      _stepMode=!!(_cvFile&&_splitPairMode&&_selVariant==='AUTO'&&_halfOrder.length>1);
      _splitStep=_stepMode?_convGetSplitStep(_cvRel,_halfOrder.length):0;
      _activeVariant=_stepMode?_halfOrder[_splitStep]:null;
      if(_stepMode)_convSetSplitStep(_cvRel,_splitStep);
      if(_previewReqBase){
        _previewReq={..._previewReqBase,preview_variant:_activeVariant||_previewReqBase.preview_variant};
        _previewKey=_convPreviewCacheKey(_previewReq);
      }
    }
  }
  if(_splitPairMode&&_cvRel&&_halfOrder.length>0){
    const _ordByRel=S._convSplitOrderByRel||(S._convSplitOrderByRel={});
    _ordByRel[_cvRel]=_halfOrder.slice();
  }
  if(_stepMode){
    _splitStep=_convGetSplitStep(_cvRel,_halfOrder.length);
    _activeVariant=_halfOrder[_splitStep];
  }
  const _canPairBySpace=_convCanShowSplitPairForOrder(_halfOrder,_cvFile);
  const _pairRange=_stepMode&&_canPairBySpace?_convGetPairRange(_halfOrder,_splitStep):null;
  const _canShowSplitPair=!!_pairRange;
  const _isSingleSplitStepMode=!!(_stepMode&&!_canShowSplitPair&&(_activeVariant==='S1'||_activeVariant==='S2'));
  if(_previewReqBase&&_activeVariant&&String(_previewReq.preview_variant).toUpperCase()!==_activeVariant){
    _previewReq={..._previewReqBase,preview_variant:_activeVariant};
    _previewKey=_convPreviewCacheKey(_previewReq);
  }
  const _canStepPrevHalf=_stepMode?(_canShowSplitPair?(_pairRange&&_pairRange.start>0):_splitStep>0):false;
  const _canStepNextHalf=_stepMode?(_canShowSplitPair?(_pairRange&&_pairRange.end<_halfOrder.length-1):_splitStep<_halfOrder.length-1):false;
  const _folioCaptureMode=!!(_cvFile&&S.convMaicPageNumbers&&S._convFolioMode);
  const _watermarkCaptureMode=!!(_cvFile&&S.convMaicWatermarks&&S._convWatermarkCapture);

  // Toolbar with convert button + status
  const tb=h('div',{className:'toolbar'});

  if(_cvFile){
    // Centered viewer toolbar: NoCrop | Reset Zoom | Close
    tb.style.justifyContent='center';
    const modes=h('div',{role:'group','aria-label':t('conv.preview_mode','Preview mode'),style:{display:'flex',gap:'2px'}});
    [['crop',t('conv.preview_crop','Crop')],['final',t('conv.preview_final','Final image')]].forEach(([value,label])=>{
      const disabled=value==='final'&&!_isNativeFormat(S.convFormat);
      const active=value===(_convUsesFinalPreview()?'final':'crop');
      modes.append(h('button',{type:'button',disabled,'aria-pressed':String(active),
        title:disabled?t('conv.preview_native_only','Available for maic formats'):t('conv.preview_final_hint','Shows crop, page size and padding. Neural restoration is not included.'),
        style:{padding:'0.25rem 0.6rem',borderRadius:'var(--radius-xs)',fontSize:'0.7rem',cursor:disabled?'default':'pointer',
          opacity:disabled?'0.4':'1',border:'1px solid var(--glass-border)',background:active?'var(--accent)':'var(--glass2)',color:active?'#fff':'var(--text3)'},
        onClick:()=>{S.convPreviewMode=value;localStorage.setItem('mcs_convPreviewMode',value);
          S._convEditMode=false;S._convFolioMode=null;S._convWatermarkCapture=false;convResetView();render();}},label));
    });
    tb.append(modes);
    const _isZoomed=S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0;
    if(_cropEnabled){
      const ncBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
        borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
        background:_isNoCrop?'var(--orange-bg)':'var(--glass2)',
        border:_isNoCrop?'1px solid rgba(251,146,60,0.3)':'1px solid var(--glass-border)',
        color:_isNoCrop?'var(--orange)':'var(--text3)'},
        onClick:()=>{
          _convToggleNoCrop(_cvFile.relPath);
          render();
        }});
      ncBtn.append(h('span',{},'\u2298'));
      ncBtn.append(h('span',{},'No Crop'));
      tb.append(ncBtn);
      // Exclude button
      const _isExcluded=!!S.convExcluded[_cvFile.relPath];
      const exBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
        borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
        background:_isExcluded?'rgba(248,113,113,0.12)':'var(--glass2)',
        border:_isExcluded?'1px solid rgba(248,113,113,0.3)':'1px solid var(--glass-border)',
        color:_isExcluded?'var(--red)':'var(--text3)'},
        title:'Exclude page from conversion',
        onClick:()=>{
          if(S.convExcluded[_cvFile.relPath]){delete S.convExcluded[_cvFile.relPath];}
          else{S.convExcluded[_cvFile.relPath]=true;}
          render();
        }});
      exBtn.append(h('span',{},'\u2715'));
      exBtn.append(h('span',{},'Exclude'));
      tb.append(exBtn);
    }
    // Bookmark button - always visible in preview
    const _bmKey=_cvFile.relPath;
    const _hasBm=!!S.convBookmarks[_bmKey];
    const bmBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
      borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
      background:_hasBm?'rgba(99,102,241,0.12)':'var(--glass2)',
      border:_hasBm?'1px solid rgba(99,102,241,0.3)':'1px solid var(--glass-border)',
      color:_hasBm?'var(--accent)':'var(--text3)'},
      title:_hasBm?'Edit bookmark: '+S.convBookmarks[_bmKey]:'Add chapter bookmark',
      onClick:()=>{S._convBookmarkEdit=!S._convBookmarkEdit;render();}});
    bmBtn.append(h('span',{},'\u2691'));
    bmBtn.append(h('span',{},_hasBm?S.convBookmarks[_bmKey]:'Bookmark'));
    tb.append(bmBtn);
    // Extra Margin button
    const _emKey=_cvFile.relPath;
    const _hasEm=!!(S.convExtraMargin[_emKey]&&(S.convExtraMargin[_emKey].top||S.convExtraMargin[_emKey].bottom||S.convExtraMargin[_emKey].left||S.convExtraMargin[_emKey].right));
    const emBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
      borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
      background:_hasEm?'rgba(34,197,94,0.12)':'var(--glass2)',
      border:_hasEm?'1px solid rgba(34,197,94,0.3)':'1px solid var(--glass-border)',
      color:_hasEm?'rgb(34,197,94)':'var(--text3)'},
      title:'Add extra margins (px)',
      onClick:()=>{S._convExtraMarginEdit=!S._convExtraMarginEdit;render();}});
    emBtn.append(h('span',{},'+'));
    emBtn.append(h('span',{},'Margin'));
    tb.append(emBtn);
    if(S.convMaicPageNumbers){
      const folioActive=!!(S._convFolioMenuOpen||S._convFolioMode);
      const folioBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.25rem 0.65rem',
        borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
        background:folioActive?'rgba(99,102,241,0.14)':'var(--glass2)',
        border:folioActive?'1px solid rgba(99,102,241,0.45)':'1px solid var(--glass-border)',
        color:folioActive?'var(--accent)':'var(--text3)'},
        title:t('conv.folio_menu_hint','Обучение распознаванию номеров страниц'),onClick:()=>{
          const open=!S._convFolioMenuOpen;
          S._convEditMode=false;S._convFolioMode=null;S._convFolioDraft=null;S._convFolioDigits='';
          S._convFolioMessage='';S._convFolioMenuOpen=open;render();
        }});
      folioBtn.append(h('span',{},'①'));
      folioBtn.append(h('span',{},t('conv.folio_menu','Page Number')));
      folioBtn.append(h('span',{style:{fontSize:'0.6rem',opacity:'0.75'}},S._convFolioMenuOpen?'▴':'▾'));
      tb.append(folioBtn);
    }
    if(S.convMaicWatermarks){
      const watermarkActive=!!(S._convWatermarkMenuOpen||S._convWatermarkCapture);
      const watermarkBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.35rem',padding:'0.25rem 0.65rem',
        borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
        background:watermarkActive?'rgba(168,85,247,0.14)':'var(--glass2)',
        border:watermarkActive?'1px solid rgba(168,85,247,0.45)':'1px solid var(--glass-border)',
        color:watermarkActive?'rgb(192,132,252)':'var(--text3)'},
        title:t('conv.watermark_button_hint','Teach maic a recurring watermark from this source'),onClick:()=>{
          const open=!S._convWatermarkMenuOpen;
          S._convEditMode=false;S._convFolioMenuOpen=false;S._convFolioMode=null;S._convFolioDraft=null;
          S._convWatermarkMenuOpen=open;S._convWatermarkCapture=open;S._convWatermarkDraft=null;
          S._convWatermarkMessage=open?t('conv.watermark_draw','Draw a rectangle around the complete watermark.'):'';
          render();
        }});
      watermarkBtn.append(h('span',{},'◇'));
      watermarkBtn.append(h('span',{},t('conv.watermarks','Watermarks')));
      tb.append(watermarkBtn);
    }
    // Edit button
    const _editKey=_cvFile.relPath;
    const _hasEdits=!!(S.convEditOps[_editKey]&&S.convEditOps[_editKey].length);
    const editBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
      borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
      background:S._convEditMode?'rgba(251,146,60,0.18)':_hasEdits?'rgba(251,146,60,0.12)':'var(--glass2)',
      border:S._convEditMode?'1px solid rgba(251,146,60,0.5)':_hasEdits?'1px solid rgba(251,146,60,0.3)':'1px solid var(--glass-border)',
      color:S._convEditMode||_hasEdits?'var(--orange)':'var(--text3)'},
      title:'Draw on image (fill areas with white/black)',
      onClick:()=>{S._convEditMode=!S._convEditMode;if(!S._convEditMode)S._convEditBrushSize=S._convEditBrushSize||20;render();}});
    editBtn.append(h('span',{},'\u270E'));
    editBtn.append(h('span',{},'Edit'));
    tb.append(editBtn);
    tb.append(h('button',{id:'convResetZoomBtn',style:{display:'flex',alignItems:'center',gap:'0.3rem',padding:'0.25rem 0.6rem',
      borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',transition:'all .2s',
      cursor:_isZoomed?'pointer':'default',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',
      color:_isZoomed?'var(--text)':'var(--text3)',opacity:_isZoomed?1:0.4},
      onClick:()=>{if(S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0){convResetView();render();}}},'Reset Zoom'));
    tb.append(h('button',{style:{display:'flex',alignItems:'center',padding:'0.25rem 0.6rem',
      borderRadius:'var(--radius-xs)',fontSize:'0.7rem',fontWeight:'500',cursor:'pointer',transition:'all .2s',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',color:'var(--text3)'},
      onClick:()=>{S.convViewIdx=null;S._convFolioMenuOpen=false;S._convFolioMode=null;S._convFolioDraft=null;S._convWatermarkMenuOpen=false;S._convWatermarkCapture=false;S._convWatermarkDraft=null;convResetView();render();},
      onMouseover:function(){this.style.color='var(--red)';this.style.borderColor='rgba(248,113,113,0.3)';},
      onMouseout:function(){this.style.color='var(--text3)';this.style.borderColor='var(--glass-border)';}},'\u2715 Close'));
  } else if(cs.converting){
    // Encoding-normalized comment.
    tb.style.position='relative';
    tb.style.overflow='hidden';
    // Encoding-normalized comment.
    const tbProg=h('div',{id:'tbProgressFill',style:{
      position:'absolute',left:'4px',top:'4px',bottom:'4px',
      width:'calc('+(cs.progress||0)+'% - 8px)',
      background:'linear-gradient(90deg,rgba(99,102,241,0.18),rgba(139,92,246,0.12))',
      borderRadius:'var(--radius-xs)',
      transition:'width .4s ease',pointerEvents:'none',zIndex:0,
      borderRight: cs.progress>0 ? '1px solid rgba(99,102,241,0.3)' : 'none'
    }});
    tb.append(tbProg);
    // Encoding-normalized comment.
    tb.append(h('span',{id:'tbProgressPhase',style:{position:'relative',zIndex:1,fontSize:'0.75rem',color:'var(--text2)'}},
      cs.phase||t('conv.converting','Converting...')));
    tb.append(h('span',{id:'tbProgressPct',style:{position:'relative',zIndex:1,fontSize:'0.75rem',color:'var(--accent)',fontWeight:'700',marginLeft:'0.3rem'}},
      (cs.progress||0)+'%'));
  }
  main.append(tb);

  if(_cvFile&&S._convFolioMenuOpen){
    const decision=_previewMeta&&_previewMeta.maic_page_number_decision;
    const detectedBoxes=decision&&Array.isArray(decision.boxes)?decision.boxes:[];
    // A spread can carry a number per half; with two finds the wrong one is
    // for the user to point at, not for the menu to guess.
    const detectedBox=detectedBoxes.length===1&&Array.isArray(detectedBoxes[0])&&detectedBoxes[0].length===4?detectedBoxes[0]:null;
    const menuBar=h('div',{style:{display:'flex',alignItems:'stretch',justifyContent:'center',gap:'0.5rem',
      padding:'0.55rem 0.8rem',background:'var(--glass)',borderBottom:'1px solid var(--glass-border)',flexWrap:'wrap'}});
    const menuChoice=(color,iconText,label,description,onClick)=>{
      const button=h('button',{style:{display:'flex',alignItems:'center',gap:'0.55rem',minWidth:'13rem',maxWidth:'22rem',
        padding:'0.5rem 0.7rem',borderRadius:'9px',cursor:'pointer',textAlign:'left',background:color+'12',
        border:'1px solid '+color+'45',color:'var(--text)',transition:'all .2s'},onClick});
      button.append(h('span',{style:{display:'grid',placeItems:'center',width:'1.55rem',height:'1.55rem',borderRadius:'7px',
        flexShrink:0,background:color+'20',color,fontWeight:'700'}},iconText));
      const copy=h('span',{style:{display:'flex',flexDirection:'column',gap:'0.12rem'}});
      copy.append(h('span',{style:{fontSize:'0.72rem',fontWeight:'650'}},label));
      copy.append(h('span',{style:{fontSize:'0.62rem',lineHeight:'1.25',color:'var(--text3)'}},description));
      button.append(copy);return button;
    };
    menuBar.append(menuChoice('#22c55e','＋',t('conv.folio_missed','Пропущен'),
      t('conv.folio_missed_menu_hint','Номер остался на странице — выделите его вручную.'),()=>{
        S._convEditMode=false;S._convFolioMenuOpen=false;convResetView();
        S._convFolioMode='number';S._convFolioDraft=null;S._convFolioDigits='';S._convFolioMessage='';render();
      }));
    menuBar.append(menuChoice('#ef4444','×',t('conv.folio_false','Это не номер'),
      detectedBox?t('conv.folio_false_auto_hint','Откроем оригинал и выделим удалённое место.'):
        t('conv.folio_false_manual_hint','Откроем оригинал — выделите ошибочно удалённое место.'),()=>{
        S._convEditMode=false;S._convFolioMenuOpen=false;convResetView();
        S._convFolioMode='not_number';S._convFolioDigits='';S._convFolioMessage='';
        S._convFolioDraft=detectedBox?{action:'not_number',box:detectedBox.map(value=>Math.round(Number(value))),relPath:_cvFile.relPath}:null;
        render();
      }));
    main.append(menuBar);
  }

  // Bookmark inline editor
  if(_cvFile&&S._convBookmarkEdit){
    const bmKey=_cvFile.relPath;
    const bmBar=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem',padding:'0.4rem 0.8rem',
      background:'var(--glass)',borderBottom:'1px solid var(--glass-border)'}});
    bmBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)',flexShrink:0}},'\u2691 '+t('conv.chapter_label','Chapter:')));
    const bmInp=h('input',{type:'text',value:S.convBookmarks[bmKey]||'',
      placeholder:t('conv.chapter_placeholder','Chapter name...'),
      style:{flex:'1',background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'8px',
        padding:'0.3rem 0.5rem',fontSize:'0.75rem',color:'var(--text)',outline:'none',fontFamily:'inherit',
        transition:'border-color .2s'},
      onFocus:function(){this.style.borderColor='var(--accent)';},
      onBlur:function(){this.style.borderColor='var(--glass-border)';},
      onKeydown:e=>{if(e.key==='Enter'){const v=e.target.value.trim();if(v)_convSetBookmark(bmKey,v,S.convExpandedSource);else _convDeleteBookmark(bmKey,S.convExpandedSource,true);S._convBookmarkEdit=false;render();}
        if(e.key==='Escape'){S._convBookmarkEdit=false;render();}}});
    bmBar.append(bmInp);
    bmBar.append(h('button',{style:{padding:'0.25rem 0.5rem',borderRadius:'8px',fontSize:'0.7rem',fontWeight:'600',
      cursor:'pointer',background:'var(--accent)',border:'none',color:'#fff',transition:'opacity .2s'},
      onClick:()=>{const v=bmInp.value.trim();if(v)_convSetBookmark(bmKey,v,S.convExpandedSource);else _convDeleteBookmark(bmKey,S.convExpandedSource,true);S._convBookmarkEdit=false;render();}},'\u2713'));
    if(S.convBookmarks[bmKey]){
      bmBar.append(h('button',{style:{padding:'0.25rem 0.5rem',borderRadius:'8px',fontSize:'0.7rem',
        cursor:'pointer',background:'rgba(248,113,113,0.12)',border:'1px solid rgba(248,113,113,0.3)',color:'var(--red)',transition:'all .2s'},
        onClick:()=>{_convDeleteBookmark(bmKey,S.convExpandedSource,true);S._convBookmarkEdit=false;render();}},'\u2715'));
    }
    main.append(bmBar);
    setTimeout(()=>{bmInp.focus();bmInp.select();},30);
  }

  // Extra Margin inline editor
  if(_cvFile&&S._convExtraMarginEdit){
    const emKey=_cvFile.relPath;
    const emCur=S.convExtraMargin[emKey]||{top:0,bottom:0,left:0,right:0};
    // Sync global color picker from per-image color when opening editor
    if(emCur.color){S._convExtraMarginColor=emCur.color;localStorage.setItem('mcs_convExtraMarginColor',emCur.color);}
    const emBar=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem',padding:'0.4rem 0.8rem',
      background:'var(--glass)',borderBottom:'1px solid var(--glass-border)',flexWrap:'wrap'}});
    emBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)',flexShrink:0}},'\u2795 Margin (px):'));
    const _emInpStyle={width:'3.5rem',background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'8px',
      padding:'0.3rem 0.5rem',fontSize:'0.75rem',color:'var(--text)',outline:'none',fontFamily:'inherit',
      transition:'border-color .2s',textAlign:'center'};
    const _emLabelStyle={fontSize:'0.65rem',color:'var(--text3)',flexShrink:0};
    const _mkEmField=(label,val)=>{
      const wrap=h('div',{style:{display:'flex',alignItems:'center',gap:'0.2rem'}});
      wrap.append(h('span',{style:_emLabelStyle},label));
      const inp=h('input',{type:'number',min:'0',max:'9999',step:'1',value:String(val||0),style:_emInpStyle,
        onFocus:function(){this.style.borderColor='rgb(34,197,94)';},
        onBlur:function(){this.style.borderColor='var(--glass-border)';}});
      wrap.append(inp);
      return {wrap,inp};
    };
    const emT=_mkEmField('T',emCur.top);
    const emB=_mkEmField('B',emCur.bottom);
    const emL=_mkEmField('L',emCur.left);
    const emR=_mkEmField('R',emCur.right);
    emBar.append(emT.wrap,emB.wrap,emL.wrap,emR.wrap);
    // Color toggle (white / black)
    const _emColStyle=(c)=>({width:'1.2rem',height:'1.2rem',borderRadius:'50%',cursor:'pointer',
      border:S._convExtraMarginColor===c?'2px solid rgb(34,197,94)':'2px solid var(--glass-border)',
      background:c,transition:'all .2s',flexShrink:0,boxShadow:c==='#ffffff'?'inset 0 0 0 1px rgba(0,0,0,0.12)':'none'});
    emBar.append(h('button',{style:_emColStyle('#ffffff'),title:'White fill',onClick:()=>{S._convExtraMarginColor='#ffffff';localStorage.setItem('mcs_convExtraMarginColor','#ffffff');render();}}));
    emBar.append(h('button',{style:_emColStyle('#000000'),title:'Black fill',onClick:()=>{S._convExtraMarginColor='#000000';localStorage.setItem('mcs_convExtraMarginColor','#000000');render();}}));
    const _emApply=()=>{
      const t2=Math.max(0,parseInt(emT.inp.value,10)||0);
      const b2=Math.max(0,parseInt(emB.inp.value,10)||0);
      const l2=Math.max(0,parseInt(emL.inp.value,10)||0);
      const r2=Math.max(0,parseInt(emR.inp.value,10)||0);
      if(t2||b2||l2||r2){S.convExtraMargin[emKey]={top:t2,bottom:b2,left:l2,right:r2,color:S._convExtraMarginColor};}
      else{delete S.convExtraMargin[emKey];}
      S._convExtraMarginEdit=false;_invalidateCropCaches();render();
    };
    [emT.inp,emB.inp,emL.inp,emR.inp].forEach(inp=>{
      inp.addEventListener('keydown',e=>{if(e.key==='Enter')_emApply();if(e.key==='Escape'){S._convExtraMarginEdit=false;render();}});
    });
    emBar.append(h('button',{style:{padding:'0.25rem 0.5rem',borderRadius:'8px',fontSize:'0.7rem',fontWeight:'600',
      cursor:'pointer',background:'rgb(34,197,94)',border:'none',color:'#fff',transition:'opacity .2s'},
      onClick:_emApply},'\u2713'));
    if(S.convExtraMargin[emKey]){
      emBar.append(h('button',{style:{padding:'0.25rem 0.5rem',borderRadius:'8px',fontSize:'0.7rem',
        cursor:'pointer',background:'rgba(248,113,113,0.12)',border:'1px solid rgba(248,113,113,0.3)',color:'var(--red)',transition:'all .2s'},
        onClick:()=>{delete S.convExtraMargin[emKey];S._convExtraMarginEdit=false;_invalidateCropCaches();render();}},'\u2715 Clear'));
    }
    main.append(emBar);
    setTimeout(()=>{emT.inp.focus();emT.inp.select();},30);
  }

  if(_cvFile&&(S._convFolioMode||S._convFolioMessage)){
    const draft=S._convFolioDraft;
    const folioBar=h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem',padding:'0.45rem 0.8rem',
      background:S._convFolioMode==='not_number'?'rgba(245,158,11,0.07)':'rgba(34,197,94,0.06)',
      borderBottom:'1px solid var(--glass-border)',flexWrap:'wrap'}});
    if(S._convFolioMode){
      folioBar.append(h('span',{style:{fontSize:'0.72rem',color:'var(--text2)'}},
        S._convFolioMode==='not_number'?(draft?
          t('conv.folio_false_selected','Показан оригинал. Оранжевым отмечено место ошибочного удаления.'):
          t('conv.folio_false_select','На оригинале выделите место, которое не нужно удалять.')):
          (draft?t('conv.folio_selected','Область выбрана.'):
            t('conv.folio_select','Обведите цифры прямоугольником на исходной странице.'))));
      if(draft&&draft.action==='number'){
        const digitsInput=h('input',{type:'text',inputMode:'numeric',maxLength:'4',value:S._convFolioDigits||'',
          placeholder:t('conv.folio_digits','Номер'),style:{width:'5rem',padding:'0.3rem 0.45rem',fontSize:'0.75rem',
            borderRadius:'7px',border:'1px solid var(--glass-border)',background:'var(--glass2)',color:'var(--text)'},
          onInput:e=>{S._convFolioDigits=String(e.target.value||'').replace(/\D/g,'').slice(0,4);},
          onKeydown:e=>{if(e.key==='Enter')_convSavePageNumberExample(_cvFile);}});
        folioBar.append(digitsInput);setTimeout(()=>digitsInput.focus(),20);
      }
      if(draft){
        folioBar.append(h('button',{disabled:!!S._convFolioSaving,style:{padding:'0.3rem 0.65rem',borderRadius:'7px',
          border:'none',background:'var(--accent)',color:'#fff',cursor:'pointer',fontSize:'0.7rem',fontWeight:'600'},
          onClick:()=>_convSavePageNumberExample(_cvFile)},
          S._convFolioSaving?t('conv.folio_saving','Сохраняю…'):t('conv.folio_save','Запомнить')));
      }
      folioBar.append(h('button',{style:{padding:'0.3rem 0.55rem',borderRadius:'7px',border:'1px solid var(--glass-border)',
        background:'var(--glass2)',color:'var(--text3)',cursor:'pointer',fontSize:'0.7rem'},onClick:()=>{
          S._convFolioMode=null;S._convFolioDraft=null;S._convFolioDigits='';render();
        }},t('common.cancel','Отмена')));
    }
    if(S._convFolioMessage){
      folioBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)'}},S._convFolioMessage));
    }
    main.append(folioBar);
  }

  if(_cvFile&&S._convWatermarkMenuOpen){
    const watermarkBar=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'0.5rem',
      padding:'0.5rem 0.8rem',background:'var(--glass)',borderBottom:'1px solid var(--glass-border)',flexWrap:'wrap'}});
    const removable=(S.artifactProfiles||[]).filter(profile=>profile.action==='remove');
    const profileSelect=h('select',{style:{minWidth:'10rem',padding:'0.32rem 0.45rem',fontSize:'0.7rem',
      borderRadius:'7px',border:'1px solid var(--glass-border)',background:'var(--glass2)',color:'var(--text)'}});
    profileSelect.append(h('option',{value:''},t('conv.watermark_new_profile','New watermark profile')));
    removable.forEach(profile=>profileSelect.append(h('option',{value:profile.id},`${profile.label} · ${profile.referenceCount}`)));
    const nameInput=h('input',{type:'text',maxLength:'80',value:t('conv.watermark_default_name','Watermark'),
      placeholder:t('conv.watermark_name','Watermark name'),style:{width:'10rem',padding:'0.32rem 0.45rem',fontSize:'0.7rem',
        borderRadius:'7px',border:'1px solid var(--glass-border)',background:'var(--glass2)',color:'var(--text)'}});
    profileSelect.addEventListener('change',()=>{
      const selected=removable.find(profile=>profile.id===profileSelect.value);
      if(selected)nameInput.value=selected.label;
    });
    watermarkBar.append(profileSelect,nameInput);
    if(S._convWatermarkCapture){
      const draft=S._convWatermarkDraft;
      watermarkBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)'}},draft
        ?t('conv.watermark_selected','Area selected: {width} × {height} px')
          .replace('{width}',String(draft.box[2]-draft.box[0])).replace('{height}',String(draft.box[3]-draft.box[1]))
        :t('conv.watermark_draw','Draw a rectangle around the complete watermark.')));
      if(draft)watermarkBar.append(h('button',{disabled:!!S._convWatermarkSaving,style:{padding:'0.32rem 0.7rem',borderRadius:'7px',
        border:'none',background:'rgb(168,85,247)',color:'#fff',cursor:'pointer',fontSize:'0.7rem',fontWeight:'600'},
        onClick:()=>_convSaveWatermarkDraft(_cvFile,profileSelect.value,nameInput.value)},
        S._convWatermarkSaving?t('conv.watermark_saving','Saving watermark sample…'):t('conv.watermark_save','Save sample')));
    }else{
      watermarkBar.append(h('button',{style:{padding:'0.32rem 0.7rem',borderRadius:'7px',border:'1px solid rgba(168,85,247,0.4)',
        background:'rgba(168,85,247,0.12)',color:'rgb(192,132,252)',cursor:'pointer',fontSize:'0.7rem',fontWeight:'600'},
        onClick:()=>{S._convWatermarkCapture=true;S._convWatermarkDraft=null;S._convWatermarkMessage=t('conv.watermark_draw','Draw a rectangle around the complete watermark.');render();}},
        t('conv.watermark_add_another','Add another sample')));
    }
    if(S._convWatermarkMessage)watermarkBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)'}},S._convWatermarkMessage));
    watermarkBar.append(h('button',{style:{padding:'0.3rem 0.55rem',borderRadius:'7px',border:'1px solid var(--glass-border)',
      background:'var(--glass2)',color:'var(--text3)',cursor:'pointer',fontSize:'0.7rem'},onClick:()=>{
        S._convWatermarkMenuOpen=false;S._convWatermarkCapture=false;S._convWatermarkDraft=null;S._convWatermarkMessage='';render();
      }},t('common.close','Close')));
    main.append(watermarkBar);
  }

  // Edit mode toolbar
  if(_cvFile&&S._convEditMode){
    const edBar=h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem',padding:'0.4rem 0.8rem',
      background:'var(--glass)',borderBottom:'1px solid var(--glass-border)',flexWrap:'wrap'}});
    edBar.append(h('span',{style:{fontSize:'0.7rem',color:'var(--text3)',flexShrink:0}},'\u270E Edit:'));
    // Tool buttons
    const _edBtnStyle=(active)=>({padding:'0.2rem 0.5rem',borderRadius:'6px',fontSize:'0.65rem',fontWeight:'600',
      cursor:'pointer',transition:'all .2s',border:active?'1px solid rgba(251,146,60,0.5)':'1px solid var(--glass-border)',
      background:active?'rgba(251,146,60,0.15)':'var(--glass2)',color:active?'var(--orange)':'var(--text3)'});
    edBar.append(h('button',{style:_edBtnStyle(S._convEditTool==='brush'),
      onClick:()=>{S._convEditTool='brush';render();}},'Brush'));
    edBar.append(h('button',{style:_edBtnStyle(S._convEditTool==='rect'),
      onClick:()=>{S._convEditTool='rect';render();}},'Rect'));
    // Brush size
    const bsWrap=h('div',{style:{display:'flex',alignItems:'center',gap:'0.25rem'}});
    bsWrap.append(h('span',{style:{fontSize:'0.6rem',color:'var(--text3)'}},'Size:'));
    const bsSlider=h('input',{type:'range',min:'2',max:'100',value:String(S._convEditBrushSize),
      style:{width:'4rem',accentColor:'var(--orange)'},
      onInput:e=>{S._convEditBrushSize=parseInt(e.target.value,10);
        const lbl=e.target.parentElement.querySelector('.ed-bs-lbl');if(lbl)lbl.textContent=S._convEditBrushSize;}});
    bsWrap.append(bsSlider);
    bsWrap.append(h('span',{className:'ed-bs-lbl',style:{fontSize:'0.6rem',color:'var(--text2)',minWidth:'1.5rem'}},String(S._convEditBrushSize)));
    edBar.append(bsWrap);
    // Color toggle
    const _colBtnStyle=(c)=>({width:'1.2rem',height:'1.2rem',borderRadius:'50%',cursor:'pointer',
      border:S._convEditColor===c?'2px solid var(--orange)':'2px solid var(--glass-border)',
      background:c,transition:'all .2s',flexShrink:0,boxShadow:c==='#fff'?'inset 0 0 0 1px rgba(0,0,0,0.12)':'none'});
    edBar.append(h('button',{style:_colBtnStyle('#fff'),title:'White',onClick:()=>{S._convEditColor='#fff';S._convEditTool=S._convEditTool==='picker'?'brush':S._convEditTool;render();}}));
    edBar.append(h('button',{style:_colBtnStyle('#000'),title:'Black',onClick:()=>{S._convEditColor='#000';S._convEditTool=S._convEditTool==='picker'?'brush':S._convEditTool;render();}}));
    // Eyedropper / picker tool
    edBar.append(h('button',{style:_edBtnStyle(S._convEditTool==='picker'),title:'Pick color from image',
      onClick:()=>{S._convEditTool='picker';render();}},'Picker'));
    // Current color swatch
    const _isCustomColor=S._convEditColor!=='#fff'&&S._convEditColor!=='#000';
    if(_isCustomColor){
      edBar.append(h('div',{style:{width:'1.2rem',height:'1.2rem',borderRadius:'50%',flexShrink:0,
        border:'2px solid var(--orange)',background:S._convEditColor,boxShadow:'inset 0 0 0 1px rgba(0,0,0,0.12)'},
        title:'Current: '+S._convEditColor}));
    }
    // Undo
    const _edOps=S.convEditOps[_cvFile.relPath]||[];
    edBar.append(h('button',{style:{..._edBtnStyle(false),opacity:_edOps.length?1:0.4},title:'Undo last',
      onClick:()=>{const ops=S.convEditOps[_cvFile.relPath];if(ops&&ops.length){ops.pop();if(!ops.length)delete S.convEditOps[_cvFile.relPath];render();}}},'Undo'));
    // Clear
    if(_edOps.length){
      edBar.append(h('button',{style:{padding:'0.2rem 0.5rem',borderRadius:'6px',fontSize:'0.65rem',
        cursor:'pointer',background:'rgba(248,113,113,0.12)',border:'1px solid rgba(248,113,113,0.3)',color:'var(--red)',transition:'all .2s'},
        onClick:()=>{delete S.convEditOps[_cvFile.relPath];render();}},'Clear'));
    }
    // Done
    edBar.append(h('button',{style:{padding:'0.2rem 0.5rem',borderRadius:'6px',fontSize:'0.65rem',fontWeight:'600',
      cursor:'pointer',background:'var(--orange)',border:'none',color:'#fff',transition:'opacity .2s',marginLeft:'auto'},
      onClick:()=>{S._convEditMode=false;render();}},'Done'));
    main.append(edBar);
  }

  // Encoding-normalized comment.
  const ca=h('div',{className:'canvas-area',style:Object.assign({minWidth:_CONV_CANVAS_MIN_W_PX+'px'},
    S.convViewIdx!==null?{}:{alignItems:'flex-start',justifyContent:'flex-start',overflow:'auto'})});

  if(_cvFile&&_convUsesFinalPreview()){
    _drawFinalPreview(ca,_cvFile);
    for(const direction of [-1,1]){
      const next=S.convViewIdx+direction;
      if(next<0||next>=_cvScanned.length)continue;
      ca.append(h('button',{className:'nav-btn',style:direction<0?{left:'10px'}:{right:'10px'},
        onClick:()=>{S.convViewIdx=next;convResetView();render();},innerHTML:icon(direction<0?'left':'right')}));
    }
  } else if(_cvFile){
    // Encoding-normalized comment.
    const _editFullImageView=!!((S._convEditMode||_folioCaptureMode||_watermarkCaptureMode)&&_previewReq);
    const _singleSplitUnifiedView=!!(!_editFullImageView&&!_canShowSplitPair&&_isSingleSplitStepMode&&(_activeVariant==='S1'||_activeVariant==='S2')&&_previewReq);
    const _displayPreviewReq=_convBuildDisplayPreviewRequest(_previewReq,{
      captureMode:_folioCaptureMode||_watermarkCaptureMode,
      fullImageView:_singleSplitUnifiedView||_editFullImageView,outputOrder:_halfOrder
    });
    const imgUrl=_displayPreviewReq?_convThumbUrl(_cvFile,_displayPreviewReq):(API+'/api/convert/serve-thumb?full=1&path='+encodeURIComponent(_cvFile.path));

    // Nav left
    if(_canStepPrevHalf||S.convViewIdx>0){
      ca.append(h('button',{className:'nav-btn',style:{left:'10px'},onClick:()=>{_convNavigatePreview(-1);},innerHTML:icon('left')}));
    }

    if(_canShowSplitPair&&!_editFullImageView&&_previewReq){
      const pairTransform=`translate(${S.convViewX}px,${S.convViewY}px) scale(${S.convViewScale})`;
      const pairFitFrac=0.98;
      const pairStage=h('div',{className:'conv-pair-stage',style:{display:'flex',alignItems:'center',justifyContent:'center',gap:_CONV_PAIR_GAP_PX+'px',
        width:'auto',maxWidth:'98%',height:Math.round(_CONV_PAIR_HEIGHT_FRAC*100*pairFitFrac)+'%',maxHeight:Math.round(pairFitFrac*100)+'%',minWidth:'0',minHeight:'0',
        position:'relative',padding:'0',boxSizing:'border-box',overflow:'visible',flex:'0 0 auto',
        contain:'layout style',isolation:'isolate',willChange:'transform',visibility:'hidden',
        transform:pairTransform,transformOrigin:'center center',transition:'none',cursor:'default'}});
      const pairImageReq={..._previewReq,preview_variant:'N'};
      // The overlays live inside the zoomed stage, so a distance read off the
      // screen is already multiplied by the zoom. Writing it back as a CSS
      // length would let the zoom multiply it a second time -- divide it out.
      const _pairUnzoom=v=>v/Math.max(0.0001,S.convViewScale||1);
      // Both halves hang from one height, so the pair is as wide as that height
      // times the two halves' aspect ratios put together. A panorama bisected by
      // No rotate gives halves wider than they are tall, and a height taken from
      // the canvas alone then runs the pair off the sides, where the panes clip
      // the outer edges away for good -- zooming out cannot bring them back,
      // because the clip rides inside the zoom. So take the height the canvas
      // width allows as well, and keep the smaller of the two.
      let _pairAspectSum=0;
      const _fitPairStageHeight=()=>{
        if(!pairStage.isConnected||!ca.isConnected)return;
        const caW=ca.clientWidth,caH=ca.clientHeight;
        if(!(caW>0&&caH>0))return;
        const byHeight=caH*_CONV_PAIR_HEIGHT_FRAC*pairFitFrac;
        const byWidth=_pairAspectSum>0?(((caW*pairFitFrac)-_CONV_PAIR_GAP_PX)/_pairAspectSum):byHeight;
        pairStage.style.height=Math.max(1,Math.min(byHeight,byWidth))+'px';
      };
      const mkSplitPane=(renderVariant,label,slotSide)=>{
        const vReq=pairImageReq;
        const isLeftSlot=slotSide==='left';
        const pane=h('div',{style:{position:'relative',display:'flex',alignItems:'center',justifyContent:'center',
          width:'auto',height:'100%',flex:'1 1 0',minWidth:'0',minHeight:'0',overflow:'hidden',contain:'paint'}});
        const frame=h('div',{style:{position:'relative',display:'flex',alignItems:'center',justifyContent:'center',
          width:'auto',height:'100%',minWidth:'0',minHeight:'0',flexShrink:'0',overflow:'hidden',contain:'paint',
          aspectRatio:'1/1',
          borderRadius:isLeftSlot?'var(--radius-xs) 0 0 var(--radius-xs)':'0 var(--radius-xs) var(--radius-xs) 0'}});
        const pImg=h('img',{src:_convThumbUrl(_cvFile,vReq),className:'main-canvas loaded',
          style:{display:'block',width:'100%',height:'100%',maxWidth:'none',maxHeight:'none',
            objectFit:'cover',objectPosition:'50% 50%',transform:'translateZ(0)',backfaceVisibility:'hidden',
            borderRadius:isLeftSlot?'var(--radius-xs) 0 0 var(--radius-xs)':'0 var(--radius-xs) var(--radius-xs) 0',
            boxShadow:'none'}});
        const pWrap=h('div',{style:{position:'absolute',left:'0',top:'0',width:'0',height:'0',pointerEvents:'none'}});
        const badge=h('div',{style:{position:'absolute',top:'4px',left:'4px',background:'rgba(15,23,42,0.78)',
          color:'#fff',fontSize:'0.58rem',fontWeight:'700',padding:'2px 6px',borderRadius:'999px',letterSpacing:'0.04em'}},label);
        const syncWrap=()=>{
          if(!pImg.isConnected||!frame.isConnected)return;
          const ir=pImg.getBoundingClientRect();
          const fr=frame.getBoundingClientRect();
          pWrap.style.left=_pairUnzoom(ir.left-fr.left)+'px';
          pWrap.style.top=_pairUnzoom(ir.top-fr.top)+'px';
          pWrap.style.width=_pairUnzoom(ir.width)+'px';
          pWrap.style.height=_pairUnzoom(ir.height)+'px';
        };
        pImg.addEventListener('load',()=>{syncWrap();requestAnimationFrame(()=>{if(pImg.isConnected)syncWrap();});});
        pImg.addEventListener('error',()=>{pairStage.style.visibility='visible';});
        pane.style.justifyContent=isLeftSlot?'flex-end':'flex-start';
        const ro=new ResizeObserver(syncWrap);
        ro.observe(frame);
        ro.observe(pImg);
        ro.observe(pane);
        const mo=new MutationObserver(()=>{
          if(!pImg.isConnected){ro.disconnect();mo.disconnect();}
        });
        mo.observe(document.body,{childList:true,subtree:true});
        pWrap.append(badge);
        frame.append(pImg,pWrap);
        pane.append(frame);
        return {pane,frame,img:pImg,wrap:pWrap,variant:label,renderVariant,side:slotSide,sync:syncWrap};
      };
      const leftRenderVariant='S2';
      const rightRenderVariant='S1';
      const s2=mkSplitPane(leftRenderVariant,'S2','left');
      const s1=mkSplitPane(rightRenderVariant,'S1','right');
      const _hasPairEditOps=!!(S.convEditOps[_cvFile.relPath]&&S.convEditOps[_cvFile.relPath].length);
      if(_hasPairEditOps&&!S._convEditMode&&!(_previewReq.maic_crop||_previewReq.maic_page_numbers)){
        const _applyPairEdits=()=>{
          _applyEditOps(s2.img,_cvFile.relPath,null);
          _applyEditOps(s1.img,_cvFile.relPath,null);
        };
        s2.img.addEventListener('load',_applyPairEdits);
        s1.img.addEventListener('load',_applyPairEdits);
        if(s1.img.complete&&s1.img.naturalWidth>0&&s2.img.complete&&s2.img.naturalWidth>0)_applyPairEdits();
      }
      const pairUnifiedWrap=h('div',{style:{position:'absolute',left:'0',top:'0',width:'0',height:'0',overflow:'visible',pointerEvents:'none',zIndex:'7'}});
      pairStage.append(s2.pane,s1.pane);
      pairStage.append(pairUnifiedWrap);
      ca.append(pairStage);
      const _setSlotViewport=(slot,region,natW,natH)=>{
        if(!slot||!slot.frame||!slot.img||!region)return;
        const rw=Math.max(1,parseInt(region.w,10)||1);
        const rh=Math.max(1,parseInt(region.h,10)||1);
        const rx0=Math.max(0,Math.min(Math.max(0,natW-rw),parseInt(region.x0,10)||0));
        const ry0=Math.max(0,Math.min(Math.max(0,natH-rh),parseInt(region.y0,10)||0));
        slot.frame.style.aspectRatio=rw+'/'+rh;
        const dx=Math.max(0,natW-rw);
        const dy=Math.max(0,natH-rh);
        const px=dx>0?(rx0/dx*100):50;
        const py=dy>0?(ry0/dy*100):50;
        slot.img.style.objectPosition=`${Math.max(0,Math.min(100,px)).toFixed(3)}% ${Math.max(0,Math.min(100,py)).toFixed(3)}%`;
      };
      const _pairSplitUI={wrap:null,line:null,top:null,bottom:null};
      const _resolvePreviewSplitRegs=(meta,ec)=>{
        if(!meta||!meta.natW||!meta.natH)return null;
        const cs=_convGetCustomSplitForImage(_cvFile.relPath,meta.natW,meta.natH);
        if(cs){
          return _convBuildSplitRegionsByAxis(meta.natW,meta.natH,cs.axis,cs.split);
        }
        const fullCrop={left:0,right:meta.natW-1,top:0,bottom:meta.natH-1};
        const clamped=_convClampCropToImage(meta.natW,meta.natH,ec||fullCrop);
        return _convGetPreviewSplitRegionsForCrop(meta.natW,meta.natH,clamped);
      };
      const _syncPairCustomSplitUI=()=>{
        if(!_pairSplitUI.wrap)return;
        const cs=_convGetCustomSplitForImage(_cvFile.relPath,s1.img.naturalWidth,s1.img.naturalHeight);
        if(!cs||cs.axis!=='x'){
          _pairSplitUI.wrap.style.display='none';
          return;
        }
        const rL=s2.frame.getBoundingClientRect();
        const rR=s1.frame.getBoundingClientRect();
        const rr=pairUnifiedWrap.getBoundingClientRect();
        const center=((rL.right+rR.left)/2)-rr.left;
        if(!Number.isFinite(center)||!Number.isFinite(rr.width)||rr.width<=0){
          _pairSplitUI.wrap.style.display='none';
          return;
        }
        _pairSplitUI.wrap.style.display='block';
        _pairSplitUI.wrap.style.left=_pairUnzoom(center).toFixed(3)+'px';
      };
      const _applyPairGapFromCrop=(ec,splitRegs,meta)=>{
        const _setPairLayout=(s2W,s1W)=>{
          const w2=Math.max(1,parseInt(s2W,10)||1);
          const w1=Math.max(1,parseInt(s1W,10)||1);
          s2.pane.style.flex=`${w2} 1 0`;
          s1.pane.style.flex=`${w1} 1 0`;
          s2.pane.style.justifyContent='flex-end';
          s1.pane.style.justifyContent='flex-start';
        };
        if(!meta||!meta.natW||!meta.natH){
          _setPairLayout(1,1);
          return;
        }
        const splitPreviewRegs=_resolvePreviewSplitRegs(meta,ec);
        const s2Region=_convGetRegionByVariantForCrop('S2',splitPreviewRegs,!!S.convManga);
        const s1Region=_convGetRegionByVariantForCrop('S1',splitPreviewRegs,!!S.convManga);
        if(s2Region)_setSlotViewport(s2,s2Region,meta.natW,meta.natH);
        if(s1Region)_setSlotViewport(s1,s1Region,meta.natW,meta.natH);
        const _slotAspect=reg=>{
          const w=Math.max(1,parseInt(reg&&reg.w,10)||0);
          const hh=Math.max(1,parseInt(reg&&reg.h,10)||0);
          return (reg&&reg.w&&reg.h)?(w/hh):0;
        };
        _pairAspectSum=_slotAspect(s2Region)+_slotAspect(s1Region);
        _fitPairStageHeight();
        if(!splitPreviewRegs||splitPreviewRegs.axis!=='x'){
          _setPairLayout(1,1);
          _syncPairCustomSplitUI();
          return;
        }
        const s2Weight=Math.max(1,s2Region&&s2Region.w?s2Region.w:Math.floor(meta.natW/2));
        const s1Weight=Math.max(1,s1Region&&s1Region.w?s1Region.w:(meta.natW-s2Weight));
        _setPairLayout(s2Weight,s1Weight);
        _syncPairCustomSplitUI();
      };
      const _syncPairLayoutFromCurrent=()=>{
        if(!s1.img.complete||!s2.img.complete||!(s1.img.naturalWidth>0&&s1.img.naturalHeight>0&&
          s2.img.naturalWidth>0&&s2.img.naturalHeight>0))return;
        const natW=s1.img.naturalWidth,natH=s1.img.naturalHeight;
        let ec={left:0,right:natW-1,top:0,bottom:natH-1};
        if(!_isNoCrop){
          const key=natW+'x'+natH+'|'+(_cvFile.relPath||'')+'|N';
          let local=null;
          if(S._editCrop&&S._editCropKey===key)local=S._editCrop;
          if(!local){
            const cc=S.convCustomCrop[_cvFile.relPath];
            if(cc&&cc.width===natW&&cc.height===natH)local=cc;
          }
          if(local)ec=local;
        }
        const regs=_convGetSplitRegionsForCrop(natW,natH,ec);
        _applyPairGapFromCrop(ec,regs,{natW,natH});
        _ensurePairSplitUI();
        pairStage.style.visibility='visible';
      };
      s1.img.addEventListener('load',_syncPairLayoutFromCurrent);
      s2.img.addEventListener('load',_syncPairLayoutFromCurrent);
      if(s1.img.complete&&s1.img.naturalWidth>0&&s2.img.complete&&s2.img.naturalWidth>0)_syncPairLayoutFromCurrent();
      const syncUnifiedWrap=()=>{
        if(!pairStage.isConnected||!s1.frame.isConnected||!s2.frame.isConnected)return;
        const pr=pairStage.getBoundingClientRect();
        const r1=s1.frame.getBoundingClientRect();
        const r2=s2.frame.getBoundingClientRect();
        const left=Math.min(r1.left,r2.left),top=Math.min(r1.top,r2.top);
        const right=Math.max(r1.right,r2.right),bottom=Math.max(r1.bottom,r2.bottom);
        pairUnifiedWrap.style.left=_pairUnzoom(left-pr.left)+'px';
        pairUnifiedWrap.style.top=_pairUnzoom(top-pr.top)+'px';
        pairUnifiedWrap.style.width=_pairUnzoom(Math.max(0,right-left))+'px';
        pairUnifiedWrap.style.height=_pairUnzoom(Math.max(0,bottom-top))+'px';
        _syncPairCustomSplitUI();
      };
      _convLiveSync=()=>{if(pairStage.isConnected){_fitPairStageHeight();s1.sync();s2.sync();syncUnifiedWrap();}};
      requestAnimationFrame(()=>{if(pairStage.isConnected)_convLiveSync();});

      function _ensurePairSplitUI(){
        const cs=_convGetCustomSplitForImage(_cvFile.relPath,s1.img.naturalWidth,s1.img.naturalHeight);
        if(!cs||cs.axis!=='x')return;
        if(_pairSplitUI.wrap&&_pairSplitUI.wrap.isConnected)return;
        const uiWrap=h('div',{style:{position:'absolute',top:'0',bottom:'0',width:'8px',transform:'translateX(-50%)',overflow:'visible',pointerEvents:'none',zIndex:'18',display:'none'}});
        const line=h('div',{style:{position:'absolute',left:'50%',transform:'translateX(-50%)',top:'0',bottom:'0',borderLeft:'1.5px dashed rgba(134,239,172,0.85)',pointerEvents:'auto',cursor:'ew-resize'}});
        const mkTri=(isTop)=>{
          return h('div',{style:{position:'absolute',left:'50%',transform:'translateX(-50%)',width:'10px',height:'7px',
            [isTop?'top':'bottom']:'-4px',
            background:'rgba(134,239,172,0.92)',
            clipPath:isTop?'polygon(0 0, 100% 0, 50% 100%)':'polygon(50% 0, 0 100%, 100% 100%)',
            pointerEvents:'auto',cursor:'ew-resize'}});
        };
        const topTri=mkTri(true);
        const botTri=mkTri(false);
        const startDrag=e=>{
          e.preventDefault();e.stopPropagation();
          const natW=Math.max(1,parseInt(s1.img.naturalWidth,10)||0);
          const natH=Math.max(1,parseInt(s1.img.naturalHeight,10)||0);
          if(!(natW>1&&natH>1))return;
          const csCur=_convGetCustomSplitForImage(_cvFile.relPath,natW,natH);
          if(!csCur||csCur.axis!=='x')return;
          const startSplit=csCur.split;
          const startX=e.clientX;
          const leftRect=s2.frame.getBoundingClientRect();
          const rightRect=s1.frame.getBoundingClientRect();
          const fullW=Math.max(1,(leftRect.width+rightRect.width));
          const pxPerUnit=fullW/natW;
          const onMove=ev=>{
            const dx=ev.clientX-startX;
            const nextSplit=startSplit+(dx/Math.max(0.001,pxPerUnit));
            _convSetCustomSplitForImage(_cvFile.relPath,natW,natH,nextSplit,'x');
            _applyPairGapFromCrop(null,null,{natW,natH});
            if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
          };
          const onUp=()=>{
            document.removeEventListener('mousemove',onMove);
            document.removeEventListener('mouseup',onUp);
            _invalidateCropCaches();
            render();
          };
          document.addEventListener('mousemove',onMove);
          document.addEventListener('mouseup',onUp);
        };
        line.addEventListener('mousedown',startDrag);
        topTri.addEventListener('mousedown',startDrag);
        botTri.addEventListener('mousedown',startDrag);
        uiWrap.append(line,topTri,botTri);
        pairUnifiedWrap.append(uiWrap);
        _pairSplitUI.wrap=uiWrap;
        _pairSplitUI.line=line;
        _pairSplitUI.top=topTri;
        _pairSplitUI.bottom=botTri;
        _syncPairCustomSplitUI();
      }
      _ensurePairSplitUI();

      const _updatePairTransform=()=>{
        const tr=`translate3d(${S.convViewX}px,${S.convViewY}px,0) scale(${S.convViewScale})`;
        pairStage.style.transform=tr;
        if(typeof _convLiveSync==='function'){
          requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
        }
      };
      ca.addEventListener('wheel',e=>{
        e.preventDefault();
        const delta=e.deltaY<0?1.15:1/1.15;
        const newScale=Math.max(0.5,Math.min(10,S.convViewScale*delta));
        const rect=pairStage.getBoundingClientRect();
        const cx=e.clientX-rect.left-rect.width/2;
        const cy=e.clientY-rect.top-rect.height/2;
        const ratio=newScale/S.convViewScale;
        S.convViewX=cx-(cx-S.convViewX)*ratio;
        S.convViewY=cy-(cy-S.convViewY)*ratio;
        S.convViewScale=newScale;
        _updatePairTransform();
        const zb=document.getElementById('convResetZoomBtn');
        if(zb){const z=S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0;zb.style.opacity=z?'1':'0.4';zb.style.cursor=z?'pointer':'default';zb.style.color=z?'var(--text)':'var(--text3)';}
      },{passive:false});
      let _cvDrag=false,_cvDragX=0,_cvDragY=0;
      ca.addEventListener('contextmenu',e=>e.preventDefault());
      const _cvMouseMove=e=>{
        if(!_cvDrag)return;
        S.convViewX+=e.clientX-_cvDragX;S.convViewY+=e.clientY-_cvDragY;
        _cvDragX=e.clientX;_cvDragY=e.clientY;
        _updatePairTransform();
      };
      const _cvMouseUp=e=>{
        if(_cvDrag){_cvDrag=false;ca.style.cursor=S.convViewScale>1?'grab':'default';
          const zb=document.getElementById('convResetZoomBtn');
          if(zb){const z=S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0;zb.style.opacity=z?'1':'0.4';zb.style.cursor=z?'pointer':'default';zb.style.color=z?'var(--text)':'var(--text3)';}
          document.removeEventListener('mousemove',_cvMouseMove);
          document.removeEventListener('mouseup',_cvMouseUp);}
      };
      ca.addEventListener('mousedown',e=>{
        if(e.button===2||e.button===1){
          e.preventDefault();
          _cvDrag=true;_cvDragX=e.clientX;_cvDragY=e.clientY;ca.style.cursor='grabbing';
          document.addEventListener('mousemove',_cvMouseMove);
          document.addEventListener('mouseup',_cvMouseUp);
        }
      });

      if(_isExcludedCanvas){
        [s1,s2].forEach(slot=>{
          slot.wrap.append(h('div',{style:{position:'absolute',top:'0',left:'0',width:'100%',height:'100%',
            background:'rgba(248,113,113,0.18)',borderRadius:'var(--radius-xs)',pointerEvents:'none'}}));
          slot.img.style.opacity='0.5';
        });
      }
      if(((_cropEnabled&&!_isNoCrop)||S.convMaicPageNumbers)&&!_isExcludedCanvas&&!S._convEditMode&&_previewReq&&_previewKey){
        const _pairKey=_previewKey+'|PAIR|'+s2.renderVariant+'|'+s1.renderVariant;
        const _pairReqUnified=_convBuildUnifiedCropRequest(_previewReq);
        const _pairKeyN=_pairReqUnified?(_convPreviewCacheKey(_pairReqUnified)+'|PAIR_UNIFIED'):'';
        const _drawUnifiedOverlay=(dataN)=>{
          if(!dataN||!dataN.ok)return false;
          const _effectiveCrop=()=>{
            const natW=Math.max(1,parseInt(dataN.width,10)||0);
            const natH=Math.max(1,parseInt(dataN.height,10)||0);
            const key=natW+'x'+natH+'|'+(_cvFile.relPath||'')+'|N';
            if(S._editCrop&&S._editCropKey===key)return S._editCrop;
            const cc=S.convCustomCrop[_cvFile.relPath];
            if(cc&&cc.width===natW&&cc.height===natH)return cc;
            return dataN.crop;
          };
          const tryDraw=()=>{
            const w1=s1.wrap.getBoundingClientRect();
            const w2=s2.wrap.getBoundingClientRect();
            if(w1.width>0&&w1.height>0&&w2.width>0&&w2.height>0){
              s1.sync();s2.sync();
              const ec=_effectiveCrop();
              const regs=_convGetSplitRegionsForCrop(dataN.width,dataN.height,ec);
              _applyPairGapFromCrop(ec,regs,{natW:dataN.width,natH:dataN.height});
              if(_cropEnabled&&!_isNoCrop){
                _drawCropOverlayPairSplit([{...s2,onEditCrop:_applyPairGapFromCrop},{...s1}],dataN,_cvFile.relPath);
              }else{
                const previewRegs=_convGetPreviewSplitRegionsForCrop(dataN.width,dataN.height,{
                  left:0,right:dataN.width-1,top:0,bottom:dataN.height-1
                });
                const r2=_convGetRegionByVariantForCrop(s2.renderVariant,previewRegs,!!S.convManga);
                const r1=_convGetRegionByVariantForCrop(s1.renderVariant,previewRegs,!!S.convManga);
                if(r2){_drawPageNumberRemovalMasks(s2.wrap,dataN,r2);_drawWatermarkRemovalMasks(s2.wrap,dataN,r2);}
                if(r1){_drawPageNumberRemovalMasks(s1.wrap,dataN,r1);_drawWatermarkRemovalMasks(s1.wrap,dataN,r1);}
              }
              if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function'){_convLiveSync();requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});}});
            } else setTimeout(tryDraw,60);
          };
          tryDraw();
          return true;
        };
        const _drawPairOverlay=(pairData)=>{
          const _drawSlot=(slot,data)=>{
            if(!data||!data.ok)return;
            const tryDraw=()=>{
              if(slot.img.naturalWidth>0&&slot.img.naturalHeight>0){
                slot.sync();
                if(_cropEnabled&&!_isNoCrop)_drawCropOverlay(slot.wrap,slot.img,data,_cvFile.relPath);
                _drawPageNumberRemovalMasks(slot.wrap,data,null);
                _drawWatermarkRemovalMasks(slot.wrap,data,null);
              }
              else setTimeout(tryDraw,80);
            };
            if(slot.img.complete&&slot.img.naturalWidth>0)tryDraw();
            else slot.img.addEventListener('load',tryDraw,{once:true});
          };
          _drawSlot(s2,pairData.left);
          _drawSlot(s1,pairData.right);
          if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
        };
        _convBindPageNumberPreview(ca,_pairReqUnified,(data,req)=>{
          S._cropCachePairUnified={key:_convPreviewCacheKey(req)+'|PAIR_UNIFIED',data};
          _drawUnifiedOverlay(data);
        });
        if(S._cropCachePairUnified&&S._cropCachePairUnified.key===_pairKeyN&&S._cropCachePairUnified.data){
          _drawUnifiedOverlay(S._cropCachePairUnified.data);
        } else {
          (async()=>{
            try{
              if(_pairReqUnified){
                const rN=await _convFetchCropPreview(_pairReqUnified);
                const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
                const now=sc&&S.convViewIdx!==null&&S.convViewIdx>=0?sc[S.convViewIdx]:null;
                if(!now||now.path!==_cvFile.path||!ca.isConnected||
                  ca._pageNumberPreviewKey!==_convPreviewCacheKey(_pairReqUnified))return;
                if(rN.ok){
                  S._cropCachePairUnified={key:_pairKeyN,data:rN};
                  _drawUnifiedOverlay(rN);
                  return;
                }
              }
              if(S._cropCachePair&&S._cropCachePair.key===_pairKey&&S._cropCachePair.data){
                _drawPairOverlay(S._cropCachePair.data);
                return;
              }
              const [rLeft,rRight]=await Promise.all([
                _convFetchCropPreview({..._previewReq,preview_variant:s2.renderVariant}),
                _convFetchCropPreview({..._previewReq,preview_variant:s1.renderVariant})
              ]);
              if(rLeft.ok&&rRight.ok){
                S._cropCachePair={key:_pairKey,data:{left:rLeft,right:rRight}};
                _drawPairOverlay(S._cropCachePair.data);
              }
            }catch(e){console.warn('crop-preview pair error:',e);}
          })();
        }
      }
    } else {
      // Image with zoom/pan - wrapped in container for crop overlay
      const imgTransform=`translate(${S.convViewX}px,${S.convViewY}px) scale(${S.convViewScale})`;
      const _emData=!_singleSplitUnifiedView&&_cvFile?S.convExtraMargin[_cvFile.relPath]:null;
      const _hasExtraMargin=!!(_emData&&((_emData.top||0)+(_emData.bottom||0)+(_emData.left||0)+(_emData.right||0))>0);
      const imgFrame=_singleSplitUnifiedView?h('div',{style:{position:'relative',display:'flex',alignItems:'center',justifyContent:'center',
        width:'auto',height:'auto',maxWidth:'98%',maxHeight:'98%',overflow:'hidden',borderRadius:'var(--radius-xs)',
        transform:imgTransform,transformOrigin:'center center',transition:'none',cursor:'default',aspectRatio:'1/1'}}):null;
      // Encoding-normalized comment.
      const img=h('img',{src:imgUrl,className:'main-canvas loaded',style:_singleSplitUnifiedView?
        {display:'block',width:'100%',height:'100%',maxWidth:'none',maxHeight:'none',objectFit:'cover',objectPosition:'50% 50%',
          transform:'translateZ(0)',backfaceVisibility:'hidden'}:
        {transform:imgTransform,transformOrigin:'center center',transition:'none',cursor:'default',maxWidth:'98%',maxHeight:'98%'}});
      if(imgFrame)imgFrame.append(img);
      let _transformEl=imgFrame||img;
      // Encoding-normalized comment.
      // Encoding-normalized comment.
      const imgWrap=h('div',{style:{position:'absolute',pointerEvents:'none',transformOrigin:'center center'}});
      const _syncWrap=()=>{
        if(!_transformEl.isConnected||!ca.isConnected)return;
        const r=_transformEl.getBoundingClientRect();
        const cr=ca.getBoundingClientRect();
        imgWrap.style.left=(r.left-cr.left)+'px';
        imgWrap.style.top=(r.top-cr.top)+'px';
        imgWrap.style.width=r.width+'px';
        imgWrap.style.height=r.height+'px';
        imgWrap.style.transform='none';
      };
      if(_hasExtraMargin&&(!_cropEnabled||_isNoCrop||_isExcludedCanvas)){
        const _applyMargin=()=>{_applyExtraMarginFrame(img,_cvFile.relPath,_syncWrap);};
        img.addEventListener('load',_applyMargin);
        if(img.complete&&img.naturalWidth>0)_applyMargin();
      }
      // Apply edit ops to preview (non-edit mode — bake into img src)
      const _hasEditOps=!!(S.convEditOps[_cvFile.relPath]&&S.convEditOps[_cvFile.relPath].length);
      if(_hasEditOps&&!S._convEditMode&&!_watermarkCaptureMode&&!(_previewReq&&(_previewReq.maic_crop||_previewReq.maic_page_numbers))){
        const _applyEdits=()=>{_applyEditOps(img,_cvFile.relPath,_syncWrap);};
        img.addEventListener('load',_applyEdits);
        if(img.complete&&img.naturalWidth>0)_applyEdits();
      }
      img.addEventListener('load',()=>{_syncWrap();requestAnimationFrame(()=>{if(_transformEl.isConnected)_syncWrap();});});
      // Encoding-normalized comment.
      const _roWrap = new ResizeObserver(_syncWrap);
      _roWrap.observe(_transformEl);
      _roWrap.observe(ca);
      ca.addEventListener('scroll',_syncWrap,{passive:true});
      // Encoding-normalized comment.
      const _roCleanup = new MutationObserver(()=>{
        if(!_transformEl.isConnected){_roWrap.disconnect();_roCleanup.disconnect();ca.removeEventListener('scroll',_syncWrap);}
      });
      _roCleanup.observe(document.body,{childList:true,subtree:true});
      _convLiveSync=()=>{if(_transformEl.isConnected)_syncWrap();};
      requestAnimationFrame(()=>{if(_transformEl.isConnected)_syncWrap();});

      const _applySingleSplitFromCrop=(ec,splitRegs,meta)=>{
        if(!_singleSplitUnifiedView||!imgFrame)return;
        const natW=Math.max(1,parseInt((meta&&meta.natW)||img.naturalWidth,10)||0);
        const natH=Math.max(1,parseInt((meta&&meta.natH)||img.naturalHeight,10)||0);
        if(!(natW>0&&natH>0))return;
        const cs=_convGetCustomSplitForImage(_cvFile.relPath,natW,natH);
        let regs=null;
        if(cs){
          regs=_convBuildSplitRegionsByAxis(natW,natH,cs.axis,cs.split);
        }
        if(!regs){
          const fullCrop={left:0,right:natW-1,top:0,bottom:natH-1};
          const clamped=_convClampCropToImage(natW,natH,(!_isNoCrop&&ec)?ec:fullCrop);
          regs=_convGetPreviewSplitRegionsForCrop(natW,natH,clamped);
        }
        const region=_convGetRegionByVariantForCrop(_activeVariant,regs,!!S.convManga);
        if(!region)return;
        const rw=Math.max(1,parseInt(region.w,10)||1);
        const rh=Math.max(1,parseInt(region.h,10)||1);
        const rx0=Math.max(0,Math.min(Math.max(0,natW-rw),parseInt(region.x0,10)||0));
        const ry0=Math.max(0,Math.min(Math.max(0,natH-rh),parseInt(region.y0,10)||0));
        imgFrame.style.aspectRatio=rw+'/'+rh;
        const dx=Math.max(0,natW-rw);
        const dy=Math.max(0,natH-rh);
        const px=dx>0?(rx0/dx*100):50;
        const py=dy>0?(ry0/dy*100):50;
        img.style.objectPosition=`${Math.max(0,Math.min(100,px)).toFixed(3)}% ${Math.max(0,Math.min(100,py)).toFixed(3)}%`;
        _syncWrap();
      };
      const _syncSingleSplitFromState=()=>{
        if(!_singleSplitUnifiedView)return;
        const natW=Math.max(1,parseInt(img.naturalWidth,10)||0);
        const natH=Math.max(1,parseInt(img.naturalHeight,10)||0);
        if(!(natW>0&&natH>0))return;
        let ec={left:0,right:natW-1,top:0,bottom:natH-1};
        if(!_isNoCrop){
          const key=natW+'x'+natH+'|'+(_cvFile.relPath||'')+'|N';
          let local=null;
          if(S._editCrop&&S._editCropKey===key)local=S._editCrop;
          if(!local){
            const cc=S.convCustomCrop[_cvFile.relPath];
            if(cc&&cc.width===natW&&cc.height===natH)local=cc;
          }
          if(local)ec=local;
        }
        _applySingleSplitFromCrop(ec,null,{natW,natH});
      };
      if(_singleSplitUnifiedView){
        img.addEventListener('load',_syncSingleSplitFromState);
        if(img.complete&&img.naturalWidth>0)_syncSingleSplitFromState();
      }

      const _updateTransform=()=>{
        const tr=`translate(${S.convViewX}px,${S.convViewY}px) scale(${S.convViewScale})`;
        _transformEl.style.transform=tr;
        _syncWrap();
      };
      // Wheel zoom
      ca.addEventListener('wheel',e=>{
        e.preventDefault();
        const delta=e.deltaY<0?1.15:1/1.15;
        const newScale=Math.max(0.5,Math.min(10,S.convViewScale*delta));
        const rect=imgWrap.getBoundingClientRect();
        const cx=e.clientX-rect.left-rect.width/2;
        const cy=e.clientY-rect.top-rect.height/2;
        const ratio=newScale/S.convViewScale;
        S.convViewX=cx-(cx-S.convViewX)*ratio;
        S.convViewY=cy-(cy-S.convViewY)*ratio;
        S.convViewScale=newScale;
        _updateTransform();
        const zb=document.getElementById('convResetZoomBtn');
        if(zb){const z=S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0;zb.style.opacity=z?'1':'0.4';zb.style.cursor=z?'pointer':'default';zb.style.color=z?'var(--text)':'var(--text3)';}
      },{passive:false});
      // RMB/MMB drag pan + Alt+LMB
      let _cvDrag=false,_cvDragX=0,_cvDragY=0;
      ca.addEventListener('contextmenu',e=>e.preventDefault());
      const _cvMouseMove=e=>{
        if(!_cvDrag)return;
        S.convViewX+=e.clientX-_cvDragX;S.convViewY+=e.clientY-_cvDragY;
        _cvDragX=e.clientX;_cvDragY=e.clientY;
        _updateTransform();
      };
      const _cvMouseUp=e=>{
        if(_cvDrag){_cvDrag=false;ca.style.cursor=S.convViewScale>1?'grab':'default';
          const zb=document.getElementById('convResetZoomBtn');
          if(zb){const z=S.convViewScale!==1||S.convViewX!==0||S.convViewY!==0;zb.style.opacity=z?'1':'0.4';zb.style.cursor=z?'pointer':'default';zb.style.color=z?'var(--text)':'var(--text3)';}
          document.removeEventListener('mousemove',_cvMouseMove);
          document.removeEventListener('mouseup',_cvMouseUp);}
      };
      ca.addEventListener('mousedown',e=>{
        if(e.button===2||e.button===1){
          e.preventDefault();
          _cvDrag=true;_cvDragX=e.clientX;_cvDragY=e.clientY;ca.style.cursor='grabbing';
          document.addEventListener('mousemove',_cvMouseMove);
          document.addEventListener('mouseup',_cvMouseUp);
        }
      });

      if(imgFrame)ca.append(imgFrame);
      else ca.append(img);
      ca.append(imgWrap);

      if(_folioCaptureMode&&!_singleSplitUnifiedView){
        const folioCanvas=h('canvas',{className:'main-canvas loaded',style:{
          transform:imgTransform,transformOrigin:'center center',transition:'none',maxWidth:'98%',maxHeight:'98%',
          cursor:'crosshair',touchAction:'none'}});
        let selectionStart=null;
        let selectionNow=null;
        const getSelectionPos=e=>{
          const rect=folioCanvas.getBoundingClientRect();
          return {
            x:Math.max(0,Math.min(folioCanvas.width,Math.round((e.clientX-rect.left)*folioCanvas.width/Math.max(1,rect.width)))),
            y:Math.max(0,Math.min(folioCanvas.height,Math.round((e.clientY-rect.top)*folioCanvas.height/Math.max(1,rect.height))))
          };
        };
        const drawSelection=()=>{
          const ctx=folioCanvas.getContext('2d');
          ctx.clearRect(0,0,folioCanvas.width,folioCanvas.height);
          ctx.drawImage(img,0,0,folioCanvas.width,folioCanvas.height);
          let box=null;
          if(selectionStart&&selectionNow){
            box=[Math.min(selectionStart.x,selectionNow.x),Math.min(selectionStart.y,selectionNow.y),
              Math.max(selectionStart.x,selectionNow.x),Math.max(selectionStart.y,selectionNow.y)];
          }else if(S._convFolioDraft&&S._convFolioDraft.action===S._convFolioMode){box=S._convFolioDraft.box;}
          if(box){
            const color=S._convFolioMode==='number'?'#22c55e':'#f59e0b';
            ctx.save();ctx.fillStyle=color+'24';ctx.strokeStyle=color;ctx.lineWidth=Math.max(2,folioCanvas.width/500);
            ctx.setLineDash([Math.max(5,folioCanvas.width/120),Math.max(3,folioCanvas.width/200)]);
            ctx.fillRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);
            ctx.strokeRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);ctx.restore();
          }
        };
        const initSelection=()=>{folioCanvas.width=img.naturalWidth||1;folioCanvas.height=img.naturalHeight||1;drawSelection();};
        img.addEventListener('load',initSelection);if(img.complete&&img.naturalWidth>0)setTimeout(initSelection,30);
        img.style.display='none';_transformEl=folioCanvas;_roWrap.observe(folioCanvas);
        if(img.parentElement)img.parentElement.insertBefore(folioCanvas,img.nextSibling);else ca.insertBefore(folioCanvas,imgWrap);
        folioCanvas.addEventListener('mousedown',e=>{
          if(e.button!==0)return;e.preventDefault();e.stopPropagation();
          selectionStart=getSelectionPos(e);selectionNow=selectionStart;drawSelection();
        });
        folioCanvas.addEventListener('mousemove',e=>{
          if(!selectionStart)return;selectionNow=getSelectionPos(e);drawSelection();
        });
        const finishSelection=e=>{
          if(!selectionStart)return;
          selectionNow=getSelectionPos(e);
          const x1=Math.min(selectionStart.x,selectionNow.x),y1=Math.min(selectionStart.y,selectionNow.y);
          const x2=Math.max(selectionStart.x,selectionNow.x),y2=Math.max(selectionStart.y,selectionNow.y);
          selectionStart=null;selectionNow=null;
          if(x2-x1>=3&&y2-y1>=3){
            S._convFolioDraft={action:S._convFolioMode,box:[x1,y1,x2,y2],relPath:_cvFile.relPath};render();
          }else drawSelection();
        };
        folioCanvas.addEventListener('mouseup',finishSelection);
        folioCanvas.addEventListener('mouseleave',e=>{if(selectionStart)finishSelection(e);});
      }

      if(_watermarkCaptureMode&&!_singleSplitUnifiedView){
        const watermarkCanvas=h('canvas',{className:'main-canvas loaded',style:{
          transform:imgTransform,transformOrigin:'center center',transition:'none',maxWidth:'98%',maxHeight:'98%',
          cursor:'crosshair',touchAction:'none'}});
        let selectionStart=null;
        let selectionNow=null;
        const getSelectionPos=e=>{
          const rect=watermarkCanvas.getBoundingClientRect();
          return {
            x:Math.max(0,Math.min(watermarkCanvas.width,Math.round((e.clientX-rect.left)*watermarkCanvas.width/Math.max(1,rect.width)))),
            y:Math.max(0,Math.min(watermarkCanvas.height,Math.round((e.clientY-rect.top)*watermarkCanvas.height/Math.max(1,rect.height))))
          };
        };
        const drawSelection=()=>{
          const ctx=watermarkCanvas.getContext('2d');
          ctx.clearRect(0,0,watermarkCanvas.width,watermarkCanvas.height);
          ctx.drawImage(img,0,0,watermarkCanvas.width,watermarkCanvas.height);
          let box=null;
          if(selectionStart&&selectionNow){
            box=[Math.min(selectionStart.x,selectionNow.x),Math.min(selectionStart.y,selectionNow.y),
              Math.max(selectionStart.x,selectionNow.x),Math.max(selectionStart.y,selectionNow.y)];
          }else if(S._convWatermarkDraft){box=S._convWatermarkDraft.box;}
          if(box){
            ctx.save();ctx.fillStyle='rgba(168,85,247,0.14)';ctx.strokeStyle='rgb(192,132,252)';
            ctx.lineWidth=Math.max(2,watermarkCanvas.width/500);
            ctx.setLineDash([Math.max(5,watermarkCanvas.width/120),Math.max(3,watermarkCanvas.width/200)]);
            ctx.fillRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);
            ctx.strokeRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);ctx.restore();
          }
        };
        const initSelection=()=>{watermarkCanvas.width=img.naturalWidth||1;watermarkCanvas.height=img.naturalHeight||1;drawSelection();};
        img.addEventListener('load',initSelection);if(img.complete&&img.naturalWidth>0)setTimeout(initSelection,30);
        img.style.display='none';_transformEl=watermarkCanvas;_roWrap.observe(watermarkCanvas);
        if(img.parentElement)img.parentElement.insertBefore(watermarkCanvas,img.nextSibling);else ca.insertBefore(watermarkCanvas,imgWrap);
        watermarkCanvas.addEventListener('mousedown',e=>{
          if(e.button!==0)return;e.preventDefault();e.stopPropagation();
          selectionStart=getSelectionPos(e);selectionNow=selectionStart;drawSelection();
        });
        watermarkCanvas.addEventListener('mousemove',e=>{
          if(!selectionStart)return;selectionNow=getSelectionPos(e);drawSelection();
        });
        const finishSelection=e=>{
          if(!selectionStart)return;
          selectionNow=getSelectionPos(e);
          const x1=Math.min(selectionStart.x,selectionNow.x),y1=Math.min(selectionStart.y,selectionNow.y);
          const x2=Math.max(selectionStart.x,selectionNow.x),y2=Math.max(selectionStart.y,selectionNow.y);
          selectionStart=null;selectionNow=null;
          if(x2-x1>=4&&y2-y1>=4){
            S._convWatermarkDraft={box:[x1,y1,x2,y2],relPath:_cvFile.relPath};
            S._convWatermarkMessage=t('conv.watermark_confirm','Confirm the selected watermark sample.');render();
          }else drawSelection();
        };
        watermarkCanvas.addEventListener('mouseup',finishSelection);
        watermarkCanvas.addEventListener('mouseleave',e=>{if(selectionStart)finishSelection(e);});
      }

      // Edit mode: replace img with canvas in-place
      if(S._convEditMode&&!_singleSplitUnifiedView){
        const _editCanvas=h('canvas',{className:'main-canvas loaded',style:{
          transform:imgTransform,transformOrigin:'center center',transition:'none',
          maxWidth:'98%',maxHeight:'98%',
          cursor:S._convEditTool==='picker'?'crosshair':S._convEditTool==='rect'?'crosshair':'none'}});
        let _edPainting=false,_edLastPos=null,_edRectStart=null,_edCursorPos=null;
        let _edCurrentStroke=null;
        const _edGetPos=(e)=>{
          const r=_editCanvas.getBoundingClientRect();
          const scaleX=_editCanvas.width/r.width;
          const scaleY=_editCanvas.height/r.height;
          return {x:Math.round((e.clientX-r.left)*scaleX),y:Math.round((e.clientY-r.top)*scaleY)};
        };
        const _edRedraw=()=>{
          const ctx=_editCanvas.getContext('2d');
          ctx.clearRect(0,0,_editCanvas.width,_editCanvas.height);
          ctx.drawImage(img,0,0,_editCanvas.width,_editCanvas.height);
          _replayEditOps(ctx,S.convEditOps[_cvFile.relPath]||[]);
          if(_edCursorPos&&S._convEditTool==='brush'){
            ctx.strokeStyle='rgba(255,255,255,0.6)';ctx.lineWidth=1;
            ctx.beginPath();ctx.arc(_edCursorPos.x,_edCursorPos.y,S._convEditBrushSize/2,0,Math.PI*2);ctx.stroke();
            ctx.fillStyle='rgba(0,0,0,0.15)';ctx.fill();
          }
        };
        const _edInit=()=>{
          _editCanvas.width=img.naturalWidth||1;
          _editCanvas.height=img.naturalHeight||1;
          _edRedraw();
        };
        img.addEventListener('load',_edInit);
        if(img.complete&&img.naturalWidth>0)setTimeout(_edInit,30);
        // Replace img with canvas in the same layout slot
        img.style.display='none';
        _transformEl=_editCanvas;
        _roWrap.observe(_editCanvas);
        if(img.parentElement)img.parentElement.insertBefore(_editCanvas,img.nextSibling);
        else ca.insertBefore(_editCanvas,imgWrap);
        // Drawing events (LMB only)
        _editCanvas.addEventListener('mousedown',e=>{
          if(e.button!==0)return;
          e.preventDefault();
          const p=_edGetPos(e);
          const ctx=_editCanvas.getContext('2d');
          if(S._convEditTool==='picker'){
            const imgCanvas=document.createElement('canvas');
            imgCanvas.width=img.naturalWidth;imgCanvas.height=img.naturalHeight;
            const imgCtx=imgCanvas.getContext('2d');
            imgCtx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight);
            const px=imgCtx.getImageData(p.x,p.y,1,1).data;
            S._convEditColor='#'+((1<<24)+(px[0]<<16)+(px[1]<<8)+px[2]).toString(16).slice(1);
            S._convEditTool='brush';render();
          } else if(S._convEditTool==='rect'){_edRectStart=p;}
          else{
            _edPainting=true;_edLastPos=p;
            _edCurrentStroke={type:'brush',points:[[p.x,p.y]],size:S._convEditBrushSize,color:S._convEditColor};
            ctx.fillStyle=S._convEditColor;ctx.beginPath();
            ctx.arc(p.x,p.y,S._convEditBrushSize/2,0,Math.PI*2);ctx.fill();
          }
        });
        _editCanvas.addEventListener('mousemove',e=>{
          const p=_edGetPos(e);_edCursorPos=p;
          const ctx=_editCanvas.getContext('2d');
          if(S._convEditTool==='rect'&&_edRectStart){
            _edRedraw();
            ctx.strokeStyle=S._convEditColor;
            ctx.lineWidth=2;ctx.setLineDash([6,4]);
            ctx.strokeRect(_edRectStart.x,_edRectStart.y,p.x-_edRectStart.x,p.y-_edRectStart.y);
            ctx.setLineDash([]);
          } else if(_edPainting&&_edLastPos){
            ctx.strokeStyle=S._convEditColor;ctx.lineWidth=S._convEditBrushSize;
            ctx.lineCap='round';ctx.lineJoin='round';
            ctx.beginPath();ctx.moveTo(_edLastPos.x,_edLastPos.y);ctx.lineTo(p.x,p.y);ctx.stroke();
            if(_edCurrentStroke)_edCurrentStroke.points.push([p.x,p.y]);
            _edLastPos=p;
          } else {_edRedraw();}
        });
        _editCanvas.addEventListener('mouseup',e=>{
          const p=_edGetPos(e);
          if(S._convEditTool==='rect'&&_edRectStart){
            const x=Math.min(_edRectStart.x,p.x),y=Math.min(_edRectStart.y,p.y);
            const w=Math.abs(p.x-_edRectStart.x),hh=Math.abs(p.y-_edRectStart.y);
            if(w>1&&hh>1){
              const ctx=_editCanvas.getContext('2d');
              ctx.fillStyle=S._convEditColor;ctx.fillRect(x,y,w,hh);
              if(!S.convEditOps[_cvFile.relPath])S.convEditOps[_cvFile.relPath]=[];
              S.convEditOps[_cvFile.relPath].push({type:'rect',x,y,w,h:hh,color:S._convEditColor});
            }
            _edRectStart=null;_edRedraw();
          } else if(_edPainting&&_edCurrentStroke){
            if(!S.convEditOps[_cvFile.relPath])S.convEditOps[_cvFile.relPath]=[];
            S.convEditOps[_cvFile.relPath].push(_edCurrentStroke);
            _edCurrentStroke=null;
          }
          _edPainting=false;_edLastPos=null;
        });
        _editCanvas.addEventListener('mouseleave',()=>{
          if(_edPainting&&_edCurrentStroke){
            if(!S.convEditOps[_cvFile.relPath])S.convEditOps[_cvFile.relPath]=[];
            S.convEditOps[_cvFile.relPath].push(_edCurrentStroke);
            _edCurrentStroke=null;
          }
          _edPainting=false;_edLastPos=null;_edCursorPos=null;_edRedraw();
        });
        // Wheel: Alt=resize brush, regular=zoom (handled by ca listener below)
        _editCanvas.addEventListener('wheel',e=>{
          if(e.altKey){
            e.preventDefault();e.stopPropagation();
            S._convEditBrushSize=Math.max(2,Math.min(100,S._convEditBrushSize-Math.sign(e.deltaY)*2));
            _edRedraw();
          }
          // else: let it bubble to ca's wheel handler for zoom
        },{passive:false});
      }

      if(_isExcludedCanvas){
        imgWrap.append(h('div',{style:{position:'absolute',top:'0',left:'0',width:'100%',height:'100%',
          background:'rgba(248,113,113,0.18)',borderRadius:'var(--radius-xs)',pointerEvents:'none'}}));
        img.style.opacity='0.5';
      }

      if(_isSingleSplitStepMode&&(_activeVariant==='S1'||_activeVariant==='S2')){
        imgWrap.append(h('div',{style:{position:'absolute',top:'4px',left:'4px',background:'rgba(15,23,42,0.78)',
          color:'#fff',fontSize:'0.58rem',fontWeight:'700',padding:'2px 6px',borderRadius:'999px',
          letterSpacing:'0.04em',pointerEvents:'none',zIndex:'6'}},_activeVariant));
      }

      if(_previewReq&&_previewKey&&!S._convEditMode&&!_folioCaptureMode&&!_watermarkCaptureMode){
        const _singleSplitOverlayReq=(_isSingleSplitStepMode&&_previewReq)?_convBuildUnifiedCropRequest(_previewReq):null;
        const _singleSplitOverlayKey=_singleSplitOverlayReq?_convPreviewCacheKey(_singleSplitOverlayReq)+'|SINGLE_SPLIT_UNIFIED':'';
        const _overlayReq=_singleSplitOverlayReq||_previewReq;
        const _overlayKey=_singleSplitOverlayReq?_singleSplitOverlayKey:_previewKey;
        const _doCropOverlay=(data)=>{
          if(_isExcludedCanvas||S._convEditMode)return;
          const tryDraw=()=>{
            if(img.naturalWidth>0&&img.naturalHeight>0){
              _syncWrap();
              if(_isSingleSplitStepMode&&(_activeVariant==='S1'||_activeVariant==='S2')){
                if(_cropEnabled&&!_isNoCrop){
                  _drawCropOverlayPairSplit([{
                    wrap:imgWrap,img,variant:_activeVariant,renderVariant:_activeVariant,
                    onEditCrop:_singleSplitUnifiedView?_applySingleSplitFromCrop:null
                  }],data,_cvFile.relPath);
                }else{
                  const regs=_convGetPreviewSplitRegionsForCrop(data.width,data.height,{
                    left:0,right:data.width-1,top:0,bottom:data.height-1
                  });
                  const region=_convGetRegionByVariantForCrop(_activeVariant,regs,!!S.convManga);
                  if(region){_drawPageNumberRemovalMasks(imgWrap,data,region);_drawWatermarkRemovalMasks(imgWrap,data,region);}
                }
              } else {
                if(_cropEnabled&&!_isNoCrop)_drawCropOverlay(imgWrap,img,data,_cvFile.relPath);
                _drawPageNumberRemovalMasks(imgWrap,data,null);
                _drawWatermarkRemovalMasks(imgWrap,data,null);
              }
              if(typeof _convLiveSync==='function')requestAnimationFrame(()=>{if(typeof _convLiveSync==='function'){_convLiveSync();requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});}});
            }
            else setTimeout(tryDraw,80);
          };
          if(img.complete&&img.naturalWidth>0)tryDraw();
          else img.addEventListener('load',tryDraw);
        };
        _convBindPageNumberPreview(ca,_overlayReq,(data,req)=>{
          const key=_convPreviewCacheKey(req);
          if(_singleSplitOverlayReq)S._cropCacheSingleUnified={key:key+'|SINGLE_SPLIT_UNIFIED',data};
          else S._cropCache={key,data};
          _doCropOverlay(data);
        });
        if(_singleSplitOverlayReq&&S._cropCacheSingleUnified&&S._cropCacheSingleUnified.key===_overlayKey&&S._cropCacheSingleUnified.data){
          _doCropOverlay(S._cropCacheSingleUnified.data);
        } else if(!_singleSplitOverlayReq&&S._cropCache&&S._cropCache.key===_overlayKey&&S._cropCache.data){
          _doCropOverlay(S._cropCache.data);
        } else {
          (async()=>{
            try{
              const r=await _convFetchCropPreview(_overlayReq);
              if(r.ok){
                const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
                const now=sc&&S.convViewIdx!==null&&S.convViewIdx>=0?sc[S.convViewIdx]:null;
                if(!now||now.path!==_cvFile.path||!ca.isConnected||
                  ca._pageNumberPreviewKey!==_convPreviewCacheKey(_overlayReq))return;
                if(_singleSplitOverlayReq)S._cropCacheSingleUnified={key:_overlayKey,data:r};
                else S._cropCache={key:_overlayKey,data:r};
                _doCropOverlay(r);
                // Only a newly discovered split changes the viewer layout.
                // Crop masks and sidebar folios update without replacing img.
                if(!_singleSplitOverlayReq&&_convExtractHalfOrder(r.output_variants).join('|')!==_halfOrder.join('|'))render();
              }
            }catch(e){console.warn('crop-preview error:',e);}
          })();
        }
      }
    }

    // Nav right
    if(_canStepNextHalf||(_cvScanned&&S.convViewIdx<_cvScanned.length-1)){
      ca.append(h('button',{className:'nav-btn',style:{right:'10px'},onClick:()=>{_convNavigatePreview(1);},innerHTML:icon('right')}));
    }

  } else {
    // Encoding-normalized comment.
    const settings=h('div',{className:'conv-settings'});

  // Encoding-normalized comment.
  const _presetKeys=['convProfile','convFormat','convManga','convSplitter','convHQ','convWebtoon','convUpscale',
    'convGamma','convBordersColor','convBatchSplit','convForceColor','convForcePNG','convCropping','convMaicCrop','convMaicMarginPct','convMaicWatermarks','convMaicPageNumbers','convMangaUpscale','convScanCleanup','convFacingPages','convForceSpreadPreview','convSpreadPreviewMode',
    'convCroppingPower','convPreserveMarginH','convPreserveMarginV','convSpreadShift','convMatchSpreadWidth','convScreenMargins','convKfxNoPadding','convDeleteInput','convNoProcessing','convFileFusion',
    'convNoRotate','convAutoBalanceMode','convAutoBalanceMarginPx','convAutoBalanceMarginUnit','convAutoBalanceMarginPct','convKindleDocType','convCustomJpeg','convJpegQ','convInterPanelCrop','convMetadataTitle','convVolPrefix','convAutolevel',
    'convNoAutocontrast','convColorAutocontrast','convEraseRainbow','convRotateFirst','convChunkSize','convPdfLegacy'];
  function _savePreset(){
    const old=document.getElementById('presetSaveModal');if(old)old.remove();
    const overlay=document.createElement('div');overlay.id='presetSaveModal';
    Object.assign(overlay.style,{position:'fixed',top:'0',left:'0',width:'100%',height:'100%',
      background:'rgba(0,0,0,0.55)',backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',
      zIndex:'10000',display:'flex',alignItems:'center',justifyContent:'center'});
    overlay.onclick=e=>{if(e.target===overlay)closeModal();};
    const closeModal=()=>{overlay.remove();document.removeEventListener('keydown',onKey);};
    const onKey=e=>{if(e.key==='Escape')closeModal();};
    document.addEventListener('keydown',onKey);
    const modal=document.createElement('div');
    Object.assign(modal.style,{background:'var(--bg2)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
      padding:'1.5rem',minWidth:'18rem',maxWidth:'24rem',boxShadow:'0 24px 80px rgba(0,0,0,0.5)',display:'flex',flexDirection:'column',gap:'0.7rem'});
    // Icon + Title
    const iconEl=document.createElement('div');iconEl.textContent='\uD83D\uDCCB';
    Object.assign(iconEl.style,{fontSize:'1.8rem',textAlign:'center'});modal.append(iconEl);
    const titleEl=document.createElement('div');titleEl.textContent=t('conv.preset_save_title','Save preset');
    Object.assign(titleEl.style,{fontSize:'0.85rem',fontWeight:'600',color:'var(--text)',textAlign:'center'});modal.append(titleEl);

    let selectedName='';
    const input=document.createElement('input');input.type='text';input.placeholder=t('conv.preset_name_ph','Preset name...');
    Object.assign(input.style,{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'10px',
      padding:'0.55rem 0.75rem',fontSize:'0.8rem',color:'var(--text)',outline:'none',width:'100%',boxSizing:'border-box',
      transition:'border-color .2s,box-shadow .2s'});
    input.onfocus=()=>{input.style.borderColor='var(--accent)';input.style.boxShadow='0 0 0 2px rgba(110,170,255,0.25)';};
    input.onblur=()=>{input.style.borderColor='var(--glass-border)';input.style.boxShadow='none';};
    input.oninput=()=>{selectedName='';updateList();};
    modal.append(input);

    // Existing presets list for overwrite
    const presetNames=S._presetFiles||[];
    let listEl=null;
    const updateList=()=>{if(listEl)listEl.querySelectorAll('.preset-ow-item').forEach(el=>{
      el.style.background=el.dataset.name===selectedName?'rgba(110,170,255,0.15)':'none';
      el.style.borderColor=el.dataset.name===selectedName?'rgba(110,170,255,0.3)':'transparent';
    });};
    if(presetNames.length>0){
      const label=document.createElement('div');label.textContent=t('conv.preset_overwrite','Or overwrite existing:');
      Object.assign(label.style,{fontSize:'0.7rem',color:'var(--text3)',marginBottom:'-0.3rem'});modal.append(label);
      listEl=document.createElement('div');
      Object.assign(listEl.style,{display:'flex',flexDirection:'column',gap:'0.2rem',maxHeight:'8rem',overflowY:'auto'});
      presetNames.forEach(name=>{
        const row=document.createElement('div');row.className='preset-ow-item';row.dataset.name=name;
        Object.assign(row.style,{padding:'0.4rem 0.6rem',borderRadius:'var(--radius-xs)',cursor:'pointer',
          fontSize:'0.75rem',color:'var(--text2)',transition:'all .15s',border:'1px solid transparent'});
        row.textContent=name;
        row.onmouseenter=()=>{if(selectedName!==name)row.style.background='rgba(255,255,255,0.04)';};
        row.onmouseleave=()=>{if(selectedName!==name)row.style.background='none';};
        row.onclick=()=>{selectedName=name;input.value=name;updateList();};
        listEl.append(row);
      });
      modal.append(listEl);
    }

    // Buttons
    const btnsRow=document.createElement('div');
    Object.assign(btnsRow.style,{display:'flex',gap:'0.5rem',marginTop:'0.2rem'});
    const saveBtn=document.createElement('div');
    Object.assign(saveBtn.style,{flex:'1',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      padding:'0.6rem',background:'rgba(110,170,255,0.12)',border:'1px solid rgba(110,170,255,0.25)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s',fontSize:'0.8rem',fontWeight:'500',color:'var(--accent)'});
    saveBtn.onmouseenter=()=>{saveBtn.style.background='rgba(110,170,255,0.2)';saveBtn.style.borderColor='rgba(110,170,255,0.4)';};
    saveBtn.onmouseleave=()=>{saveBtn.style.background='rgba(110,170,255,0.12)';saveBtn.style.borderColor='rgba(110,170,255,0.25)';};
    saveBtn.textContent=t('conv.preset_save_btn','Save');
    const doSave=async()=>{
      const name=input.value.trim();if(!name)return;
      closeModal();
      const data={};_presetKeys.forEach(k=>{data[k]=S[k];});
      await apiPost('/api/presets/save',{name,data});
      await _refreshPresets();S._convShowPresets=false;render();
    };
    saveBtn.onclick=doSave;
    input.onkeydown=e=>{if(e.key==='Enter')doSave();};
    btnsRow.append(saveBtn);
    const cancelBtn=document.createElement('div');
    Object.assign(cancelBtn.style,{flex:'1',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      padding:'0.6rem',background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s',fontSize:'0.8rem',fontWeight:'500',color:'var(--text2)'});
    cancelBtn.onmouseenter=()=>{cancelBtn.style.background='var(--glass3)';cancelBtn.style.borderColor='var(--accent)';};
    cancelBtn.onmouseleave=()=>{cancelBtn.style.background='var(--glass2)';cancelBtn.style.borderColor='var(--glass-border)';};
    cancelBtn.textContent=t('conv.preset_delete_cancel','Cancel');
    cancelBtn.onclick=closeModal;
    btnsRow.append(cancelBtn);
    modal.append(btnsRow);
    overlay.append(modal);document.body.append(overlay);
    setTimeout(()=>input.focus(),50);
  }
  async function _loadPreset(name){
    const r=await(await apiPost('/api/presets/load',{name})).json();
    if(!r.ok)return;
    _presetKeys.forEach(k=>{if(r.data[k]!==undefined)S[k]=r.data[k];});
    if((parseInt(S.convAutoBalanceMode)||0)>1){
      S.convAutoBalanceMode=0;
    }
    if(!['px','pct'].includes(String(S.convAutoBalanceMarginUnit||'px').toLowerCase())){
      S.convAutoBalanceMarginUnit='px';
    }
    if(!Number.isFinite(parseFloat(S.convAutoBalanceMarginPct))){
      S.convAutoBalanceMarginPct=3.0;
    }
    if(r.data.convAutoBalanceMode===undefined&&r.data.convAutoBalanceMargins!==undefined){
      const legacyOn=!!r.data.convAutoBalanceMargins;
      const legacyPx=parseInt(r.data.convAutoBalanceMarginPx)||0;
      S.convAutoBalanceMode=legacyOn?(legacyPx>0?1:0):0;
      S.convAutoBalanceMarginUnit='px';
    }
    if((parseInt(S.convAutoBalanceMode)||0)===1){
      if((S.convAutoBalanceMarginUnit||'px')==='pct' && (parseFloat(S.convAutoBalanceMarginPct)||0)<=0){
        S.convAutoBalanceMarginPct=3.0;
      }
      if((S.convAutoBalanceMarginUnit||'px')!=='pct' && (parseInt(S.convAutoBalanceMarginPx)||0)<=0){
        S.convAutoBalanceMarginPx=24;
      }
    }
    S._convShowPresets=false;render();
  }
  async function _deletePreset(name){
    await apiPost('/api/presets/delete',{name});
    await _refreshPresets();render();
  }
  function _confirmDeletePreset(name){
    const old=document.getElementById('presetDeleteModal');if(old)old.remove();
    const overlay=document.createElement('div');overlay.id='presetDeleteModal';
    Object.assign(overlay.style,{position:'fixed',top:'0',left:'0',width:'100%',height:'100%',
      background:'rgba(0,0,0,0.55)',backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',
      zIndex:'10000',display:'flex',alignItems:'center',justifyContent:'center'});
    overlay.onclick=e=>{if(e.target===overlay)overlay.remove();};
    const closeModal=()=>{overlay.remove();document.removeEventListener('keydown',onKey);};
    const onKey=e=>{if(e.key==='Escape')closeModal();};
    document.addEventListener('keydown',onKey);
    const modal=document.createElement('div');
    Object.assign(modal.style,{background:'var(--bg2)',border:'1px solid var(--glass-border2)',borderRadius:'var(--radius)',
      padding:'1.5rem',minWidth:'16rem',maxWidth:'22rem',boxShadow:'0 24px 80px rgba(0,0,0,0.5)',display:'flex',flexDirection:'column',gap:'0.7rem'});
    // Icon
    const iconEl=document.createElement('div');iconEl.textContent='\uD83D\uDDD1\uFE0F';
    Object.assign(iconEl.style,{fontSize:'1.8rem',textAlign:'center'});modal.append(iconEl);
    // Title
    const titleEl=document.createElement('div');
    titleEl.textContent=t('conv.preset_delete_title','Delete preset?');
    Object.assign(titleEl.style,{fontSize:'0.85rem',fontWeight:'600',color:'var(--text)',textAlign:'center'});modal.append(titleEl);
    // Message
    const msgEl=document.createElement('div');
    msgEl.textContent=t('conv.preset_delete_confirm','Are you sure you want to delete preset')+' В«'+name+'В»?';
    Object.assign(msgEl.style,{fontSize:'0.75rem',color:'var(--text3)',textAlign:'center',lineHeight:'1.4'});modal.append(msgEl);
    // Buttons row
    const btnsRow=document.createElement('div');
    Object.assign(btnsRow.style,{display:'flex',gap:'0.5rem',marginTop:'0.3rem'});
    // Confirm button
    const confirmBtn=document.createElement('div');
    Object.assign(confirmBtn.style,{flex:'1',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      padding:'0.6rem',background:'rgba(248,113,113,0.12)',border:'1px solid rgba(248,113,113,0.25)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s',fontSize:'0.8rem',fontWeight:'500',color:'var(--red)'});
    confirmBtn.onmouseenter=()=>{confirmBtn.style.background='rgba(248,113,113,0.2)';confirmBtn.style.borderColor='rgba(248,113,113,0.4)';};
    confirmBtn.onmouseleave=()=>{confirmBtn.style.background='rgba(248,113,113,0.12)';confirmBtn.style.borderColor='rgba(248,113,113,0.25)';};
    confirmBtn.textContent=t('conv.preset_delete_yes','Yes, delete');
    confirmBtn.onclick=()=>{closeModal();_deletePreset(name);};
    btnsRow.append(confirmBtn);
    // Cancel button
    const cancelBtn=document.createElement('div');
    Object.assign(cancelBtn.style,{flex:'1',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
      padding:'0.6rem',background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',
      cursor:'pointer',transition:'all .2s',fontSize:'0.8rem',fontWeight:'500',color:'var(--text2)'});
    cancelBtn.onmouseenter=()=>{cancelBtn.style.background='var(--glass3)';cancelBtn.style.borderColor='var(--accent)';};
    cancelBtn.onmouseleave=()=>{cancelBtn.style.background='var(--glass2)';cancelBtn.style.borderColor='var(--glass-border)';};
    cancelBtn.textContent=t('conv.preset_delete_cancel','Cancel');
    cancelBtn.onclick=closeModal;
    btnsRow.append(cancelBtn);
    modal.append(btnsRow);
    overlay.append(modal);document.body.append(overlay);
  }
  async function _refreshPresets(){
    try{const r=await(await fetch(API+'/api/presets/list')).json();S._presetFiles=r.presets||[];}catch(e){}
  }
  if(!S._presetFiles)_refreshPresets();

  const titleRow3=h('div',{style:{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:'0.2rem'}});
  const titleInfo=h('div',{});
  titleInfo.append(h('div',{style:{fontSize:'1.2rem',fontWeight:'700',color:'var(--text)',letterSpacing:'-0.02em'}},t('conv.title')));
  titleInfo.append(h('div',{style:{fontSize:'0.72rem',color:'var(--text3)',marginTop:'2px'}},t('conv.subtitle')));
  titleRow3.append(titleInfo);

  // Presets button + Convert button
  const presetWrap=h('div',{style:{position:'relative'}});
  const rightBtns=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem'}});
  const presetBtn=h('button',{style:{display:'flex',alignItems:'center',gap:'0.35rem',background:'var(--glass)',
    border:'1px solid var(--glass-border)',padding:'0.4rem 0.7rem',borderRadius:'10px',fontSize:'0.75rem',fontWeight:'500',
    color:'var(--text)',cursor:'pointer',transition:'all .2s',whiteSpace:'nowrap'},
    onClick:()=>{S._convShowPresets=!S._convShowPresets;render();}});
  presetBtn.append(h('span',{style:{color:'var(--accent)'}},'\ud83d\udccb'));
  presetBtn.append(t('conv.presets'));
  presetBtn.append(h('span',{style:{fontSize:'0.55rem',color:'var(--text3)'}},S._convShowPresets?'\u25B2':'\u25BC'));
  presetWrap.append(presetBtn);

  if(S._convShowPresets){
    const dd=h('div',{style:{position:'absolute',right:'0',top:'100%',marginTop:'4px',minWidth:'14rem',
      background:'rgba(28,28,33,0.98)',border:'1px solid var(--glass-border)',borderRadius:'12px',
      boxShadow:'0 10px 30px rgba(0,0,0,0.4)',zIndex:'100',overflow:'hidden',
      backdropFilter:'blur(12px)',WebkitBackdropFilter:'blur(12px)'}});
    const presetNames=S._presetFiles||[];
    if(presetNames.length>0){
      presetNames.forEach(name=>{
        const row=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'0.5rem 0.7rem',
          cursor:'pointer',transition:'background .15s',fontSize:'0.75rem',color:'var(--text2)'},
          onMouseover:function(){this.style.background='rgba(255,255,255,0.04)';},
          onMouseout:function(){this.style.background='none';}});
        row.append(h('span',{onClick:()=>_loadPreset(name),style:{flex:'1'}},name));
        row.append(h('span',{style:{fontSize:'0.6rem',color:'var(--text3)',cursor:'pointer',padding:'0.1rem 0.25rem',
          borderRadius:'4px'},
          onClick:e=>{e.stopPropagation();_confirmDeletePreset(name);},
          onMouseover:function(){this.style.color='var(--red)';},
          onMouseout:function(){this.style.color='var(--text3)';}},'\u2715'));
        dd.append(row);
      });
      dd.append(h('div',{style:{height:'1px',background:'var(--glass-border)'}}));
    }
    dd.append(h('div',{style:{padding:'0.5rem 0.7rem',cursor:'pointer',fontSize:'0.75rem',color:'var(--accent)',
      transition:'background .15s'},
      onClick:_savePreset,
      onMouseover:function(){this.style.background='rgba(255,255,255,0.04)';},
      onMouseout:function(){this.style.background='none';}},t('conv.save_preset')));
    presetWrap.append(dd);
  }
  rightBtns.append(presetWrap);
  titleRow3.append(rightBtns);
  settings.append(titleRow3);

  // Accordion helper
  if(!S._convAccOpen)S._convAccOpen={device:true,processing:true,advanced:false};
  const mkAccordion=(key,icon,iconBg,title,sub,buildBody)=>{
    const acc=h('div',{className:'conv-accordion'});
    const isOpen=S._convAccOpen[key];
    const hdr=h('button',{className:'conv-accordion-hdr','data-focus-key':'accordion-'+key,'aria-expanded':String(!!isOpen),onClick:()=>{S._convAccOpen[key]=!isOpen;render();}});
    const left=h('div',{className:'conv-accordion-left'});
    left.append(h('div',{className:'conv-accordion-icon',style:{background:iconBg}},icon));
    const info=h('div',{});
    info.append(h('div',{className:'conv-accordion-title'},title));
    if(sub)info.append(h('div',{className:'conv-accordion-sub'},sub));
    left.append(info);
    hdr.append(left);
    hdr.append(h('span',{className:'conv-accordion-chevron'+(isOpen?' open':'')},'\u25BC'));
    acc.append(hdr);
    if(isOpen){const body=h('div',{className:'conv-accordion-body'});buildBody(body);acc.append(body);}
    settings.append(acc);
  };

  // Resolve current profile info
  // A device kept from a preset or a previous run may not be on offer any
  // more: the KCC-less profile table is a short one, and a saved Kobo is not
  // in it. Snap before anything reads the selection, or the label and the
  // picker disagree for a render.
  if(S.convProfiles&&!Object.values(S.convProfiles).some(g=>g[S.convProfile]))
    S.convProfile=Object.keys(Object.values(S.convProfiles)[0]||{})[0]||S.convProfile;
  let _profInfo=null;
  if(S.convProfiles){Object.values(S.convProfiles).forEach(g=>{if(g[S.convProfile])_profInfo=g[S.convProfile];});}
  const _profSub=(_profInfo?_profInfo.name:'')+(S.convFormat?' \u00B7 '+S.convFormat:'');
  // Helper: get real KCC profile key for current selection
  const _kccProfileKey=_profInfo?(_profInfo.profile_key||S.convProfile):S.convProfile;

  // Encoding-normalized comment.
  const _missing=[];
  if(S.convNativeOnly) _missing.push({
    id:'kcc',
    icon:'\ud83e\uddf1',
    label:t('conv.missing.kcc','KCC'),
    sub:t('conv.missing.kcc_sub','Only the native formats are offered. Unzip KCC into /modules for the rest.'),
    url:'https://github.com/ciromattia/kcc/releases'
  });
  if(!S.conv7zAvailable) _missing.push({
    id:'7zip',
    icon:'\ud83d\udce6', label:'7-Zip', sub:'Required for CBZ/CBR archives',
    url: navigator.platform&&navigator.platform.toLowerCase().includes('win')
      ? 'https://www.7-zip.org/download.html'
      : 'https://www.7-zip.org/download.html'
  });
  if(!S.convPreviewerAvailable) _missing.push({
    id:'previewer',
    icon:'\ud83d\udcd6', label:'Kindle Previewer 3',
    sub:t('conv.missing.previewer_sub','Required for the KCC-built MOBI and KFX output, not for "MOBI maic" or "EPUB maic"'),
    url:'https://www.amazon.com/Kindle-Previewer/b?ie=UTF8&node=21381691011'
  });
  if(!S.convKfxAvailable) _missing.push({
    id:'kfxlib',
    icon:'\ud83e\udde9', label:'kfxlib',
    sub:t('conv.missing.kfxlib_sub','Bundled modules/kfxlib is missing. Restore it from the maic source archive to enable KFX output.'),
    url:null
  });
  if(_missing.length>0){
    const banner=h('div',{style:{display:'flex',flexDirection:'column',gap:'0.4rem',marginBottom:'0.25rem'}});
    const visibleMissing=_missing.filter(({id})=>!_dismissedModuleNotices.has(id));
    visibleMissing.forEach(({id,icon,label,sub,url})=>{
      const item=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem'}});
      const row=h(url?'a':'div',{...(url?{href:url,target:'_blank',rel:'noopener noreferrer'}:{}),
        style:{display:'flex',flex:'1',minWidth:0,alignItems:'center',gap:'0.6rem',padding:'0.5rem 0.75rem',
          background:'rgba(251,191,36,0.07)',border:'1px solid rgba(251,191,36,0.25)',
          borderRadius:'var(--radius-xs)',textDecoration:'none',transition:'all .2s',cursor:url?'pointer':'default'},
        onMouseover:function(){this.style.background='rgba(251,191,36,0.13)';this.style.borderColor='rgba(251,191,36,0.5)';},
        onMouseout:function(){this.style.background='rgba(251,191,36,0.07)';this.style.borderColor='rgba(251,191,36,0.25)';}});
      row.append(h('span',{style:{fontSize:'1rem'}},icon));
      const txt=h('div',{style:{flex:'1',minWidth:0}});
      txt.append(h('div',{style:{fontSize:'0.72rem',fontWeight:'500',color:'var(--text)'}},
        label+' not found'));
      txt.append(h('div',{style:{fontSize:'0.62rem',color:'var(--text3)',marginTop:'1px'}},sub));
      row.append(txt);
      if(url)row.append(h('span',{style:{fontSize:'0.65rem',color:'rgba(251,191,36,0.8)',flexShrink:0}},'Download \u2197'));
      const dismissLabel=t('conv.missing.dismiss','Hide this notice')+': '+label;
      const dismiss=h('button',{title:dismissLabel,'aria-label':dismissLabel,
        style:{flexShrink:0,width:'28px',height:'28px',padding:0,background:'transparent',
          border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',color:'var(--text3)',cursor:'pointer',fontSize:'1.1rem'},
        onClick:()=>{_dismissedModuleNotices.add(id);_persistDismissedModuleNotices();render();}},'×');
      item.append(row,dismiss);
      banner.append(item);
    });
    const hiddenCount=_missing.length-visibleMissing.length;
    if(hiddenCount)banner.append(h('button',{
      style:{alignSelf:'flex-start',padding:'0.25rem 0',background:'transparent',border:0,color:'var(--text3)',cursor:'pointer',fontSize:'0.65rem',textDecoration:'underline'},
      onClick:()=>{_missing.forEach(({id})=>_dismissedModuleNotices.delete(id));_persistDismissedModuleNotices();render();}},
      t('conv.missing.show_hidden','Show hidden module notices')+' ('+hiddenCount+')'));
    settings.append(banner);
  }

  // Encoding-normalized comment.
  mkAccordion('device','\ud83d\udcf1','rgba(96,165,250,0.12)',
    t('conv.sec_device'),_profSub,body=>{
    const grid2=h('div',{style:{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1rem'}});
    // Left col
    const colL=h('div',{style:{display:'flex',flexDirection:'column',gap:'0.8rem'}});
    // Device
    const dg=h('div',{});
    const devLabelRow=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'0.25rem'}});
    devLabelRow.append(h('div',{className:'conv-field-label',style:{margin:'0'}},t('settings.device')));
    if(_profInfo&&_profInfo.width>0)devLabelRow.append(h('span',{className:'conv-dim'},_profInfo.width+'\u00D7'+_profInfo.height+(_profInfo.profile_key?' \u00B7 '+_profInfo.profile_key:'')));
    dg.append(devLabelRow);
    const devRow=h('div',{style:{display:'flex',alignItems:'center',gap:'0.4rem'}});
    const _profOpts=S.convProfiles
      ? Object.entries(S.convProfiles).map(([group,profiles])=>({
          group, items:Object.entries(profiles).map(([key,p])=>({value:key,label:p.name}))
        }))
      : [];
    const profSel=mkCustomSelect(_profOpts,{value:S.convProfile,label:t('settings.device'),style:{flex:'1'},menuMaxHeight:'16rem',
      onChange:v=>{S.convProfile=v;render();}});
    devRow.append(profSel);
    dg.append(devRow);colL.append(dg);
    // Format
    const fg=h('div',{});
    fg.append(h('div',{className:'conv-field-label'},t('conv.format_label')));
    const _allFmts=['Auto','EPUB','EPUB maic','MOBI','MOBI+EPUB','KFX','KFX maic','KFX + MOBI maic','MOBI maic','KFX (+sdr)','CBZ','PDF','EPUB-200MB','MOBI+EPUB-200MB'];
    // Everything else is KCC writing the book, so without KCC there is nothing
    // behind those entries. 'KFX maic' writes its own container but through the
    // bundled kfxlib, whose absence means the source archive is incomplete.
    const _nativeFmts=['EPUB maic','MOBI maic','KFX maic','KFX + MOBI maic'];
    const _offeredFmts=S.convNativeOnly?_nativeFmts:_allFmts;
    // A format kept from a preset or a previous run may not be on offer any
    // more -- the same volume settings reused on a machine with no KCC. Snap
    // to something that can actually build rather than show an empty box.
    if(!_offeredFmts.includes(S.convFormat))S.convFormat=_offeredFmts[0];
    const _fmtOpts=_offeredFmts.map(f=>{
      const needsMobi=f==='MOBI'||f.startsWith('MOBI+EPUB');  // 'MOBI maic' needs no kindlegen.exe either
      const needsKfx=f==='KFX'||f==='KFX (+sdr)'||f==='KFX maic'||f==='KFX + MOBI maic';  // kindlegen is not the dependency here, kfxlib is
      let label=f;
      if(f==='EPUB-200MB')label='EPUB (200MB limit)';
      else if(f==='MOBI+EPUB-200MB')label='MOBI + EPUB (200MB limit)';
      else if(f==='MOBI+EPUB')label='MOBI + EPUB';
      if(needsMobi&&!S.convMobiAvailable)label+=(' \u26a0');
      if(needsKfx&&!S.convKfxAvailable)label+=(' \u26a0');
      return{value:f,label};
    });
    const fmtSel=mkCustomSelect(_fmtOpts,{value:S.convFormat,label:t('conv.format_label'),style:{width:'100%'},
      onChange:v=>{S.convFormat=v;render();}});
    fg.append(fmtSel);colL.append(fg);
    grid2.append(colL);
    // Right col
    const colR=h('div',{style:{display:'flex',flexDirection:'column',gap:'0.8rem'}});
    // Title + Author fields with Metadata button
    const metaRow=h('div',{style:{display:'flex',gap:'0.5rem',alignItems:'stretch'}});
    const metaFields=h('div',{style:{display:'flex',flexDirection:'column',gap:'0.8rem',flex:'1 1 50%',minWidth:0}});
    const tg=h('div',{});
    tg.append(h('div',{className:'conv-field-label'},t('conv.book_title')));
    tg.append(h('input',{className:'conv-input','aria-label':t('conv.book_title'),style:{width:'100%'},placeholder:t('conv.book_title_ph'),value:S.convTitle,onInput:e=>{S.convTitle=e.target.value;}}));
    metaFields.append(tg);
    const ag=h('div',{});
    ag.append(h('div',{className:'conv-field-label'},t('conv.author')));
    ag.append(h('input',{className:'conv-input','aria-label':t('conv.author'),style:{width:'100%'},placeholder:t('conv.book_title_ph'),value:S.convAuthor,onInput:e=>{S.convAuthor=e.target.value;}}));
    metaFields.append(ag);
    metaRow.append(metaFields);
    // Metadata / TOC buttons - full height of both rows
    const activeSrc=S.convExpandedSource||S.convSources[0]||null;
    const btnCol=h('div',{style:{
      display:'grid',
      gridTemplateRows:'1fr 1fr',
      gap:'0.5rem',
      flex:'1 1 50%',
      minWidth:'10rem',
      minHeight:'5.8rem'
    }});
    const mkMetaSideBtn=(label,title,iconHTML,onClick)=>{
      const b=h('button',{
        style:{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:'0.2rem',
          background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'var(--radius-xs)',
          width:'100%',height:'auto',minHeight:'2.65rem',padding:'0',cursor:activeSrc?'pointer':'not-allowed',
          color:activeSrc?'var(--text2)':'var(--text3)',opacity:activeSrc?'1':'0.5',
          transition:'all .2s',flexShrink:0,fontSize:'0.65rem',fontFamily:'inherit',letterSpacing:'0.05em',fontWeight:'500'},
        disabled:!activeSrc,title:activeSrc?title:t('ui.add_source_first','Add a source first'),
        onMouseover:function(){if(activeSrc){this.style.background='var(--glass3)';this.style.borderColor='var(--accent)';this.style.color='var(--accent)';}},
        onMouseout:function(){this.style.background='var(--glass2)';this.style.borderColor='var(--glass-border)';this.style.color=activeSrc?'var(--text2)':'var(--text3)';},
        onClick:activeSrc?onClick:null
      });
      b.innerHTML=iconHTML+`<span>${label}</span>`;
      return b;
    };
    const metaBtn=mkMetaSideBtn(t('ui.metadata','Metadata'),t('ui.metadata_help','Create or edit book metadata'),
      `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
      ()=>showComicInfoModal(activeSrc, S.convScanned[activeSrc]||[], 'meta'));
    const tocBtn=mkMetaSideBtn(t('ui.contents','Contents'),'Edit Table of Contents',
      `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>`,
      ()=>showComicInfoModal(activeSrc, S.convScanned[activeSrc]||[], 'toc'));
    btnCol.append(metaBtn,tocBtn);
    metaRow.append(btnCol);
    colR.append(metaRow);
    grid2.append(colR);
    body.append(grid2);
  });

  const _stateTip=(tip,marker,state)=>{
    const current=`${t('conv.state.current','Current state')}: ${marker} ${state}`;
    return tip?current+'\n\n'+tip:current;
  };
  const _stateSpan=state=>h('span',{style:{fontSize:'0.55rem',color:'var(--accent)',marginLeft:'0.15rem'}},state);
  const _isNativeFmt=_isNativeFormat(S.convFormat);
  const _nativeTip=t('conv.tip.native_ignored','Not used by native maic formats.\nPages are cropped, split and sized by maic itself, without KCC.');
  const _gateNative=el=>_isNativeFmt?_convDisableControl(el,_nativeTip):el;

  // Encoding-normalized comment.
  mkAccordion('processing','\ud83c\udf9b\ufe0f','rgba(167,139,250,0.12)',
    t('conv.sec_processing'),t('conv.sec_processing_sub'),body=>{

  const mkCheck=(label,val,setter,tip)=>{
    const key=label;label=_convOptionText(label);
    const lb=h('label',{className:'conv-check'});
    const state=val?t('conv.state.on','On'):t('conv.state.off','Off');
    if(tip)lb.setAttribute('data-tip',_stateTip(tip,val?'●':'○',state));
    const cb=h('input',{type:'checkbox','data-focus-key':'conv-'+key});cb.checked=val;
    cb.addEventListener('change',e=>{setter(e.target.checked);render();});
    lb.append(cb,label,_stateSpan(state));return lb;
  };
  const mkState=(label,val,setter,states,tip,marker,toNext)=>{
    const key=label;label=_convOptionText(label);
    const lb=h('label',{className:'conv-check'});
    const state=_convOptionText(states[val]||String(val));
    if(tip)lb.setAttribute('data-tip',_stateTip(tip,marker,state));
    const cb=h('input',{type:'checkbox','data-focus-key':'conv-'+key});
    cb.checked=val>0;cb.indeterminate=(marker==='◑');
    cb.addEventListener('click',e=>{e.preventDefault();setter(toNext(val));render();});
    lb.append(cb,label,_stateSpan(state));
    return lb;
  };
  const mkTri=(label,val,setter,states,tip)=>
    mkState(label,val,setter,states,tip,['○','◑','●'][val]||'○',v=>(v+1)%3);
  const mkDual=(label,val,setter,states,tip)=>
    mkState(label,val,setter,states,tip,val===1?'●':'○',v=>(v===1?0:1));

  const grid=h('div',{className:'conv-grid'});
  grid.append(mkCheck('Right-to-left (manga)',S.convManga,v=>{S.convManga=v;},
    t('conv.tip.manga_rtl','Enable right-to-left reading.')));
  const _isKfxFmt=(S.convFormat||'').toUpperCase().startsWith('KFX');
  // Every native format crops, splits and sizes pages
  // themselves (one shared pipeline), so KCC's own image options never run
  // for them.  Dim them rather than let them look effective.
  const _splitterDisabled=_isKfxFmt||_isNativeFmt;
  const _splitterEl=mkTri('Spread splitter',_splitterDisabled?0:S.convSplitter,v=>{if(!_splitterDisabled){S.convSplitter=v;}render();},
    {0:'Off',1:'Rotate',2:'Split+Rot'},
    _splitterDisabled?(_isNativeFmt?t('conv.tip.spread_splitter_maic','Spread splitter is disabled for this format.\nmaic decides from the page itself: wider than 1.16 it is a spread and is cut in half; past 1.8 it is a panorama and is turned instead, unless No rotate is on — then that one is cut too.\nThe preview follows the same rule.'):t('conv.tip.spread_splitter_kfx','Spread splitter is disabled for this format.\nSpreads are handled natively as wide images.')):t('conv.tip.spread_splitter','○ Off — No spread processing.\n◑ Rotate — Spreads will be rotated.\n● Split+Rotate — Displayed twice: first split, then rotated.'));
  if(_splitterDisabled)_convDisableControl(_splitterEl);
  grid.append(_splitterEl);
  const _panelEl=mkTri('Panel View 4/2/HQ',_isKfxFmt?0:S.convHQ,v=>{if(!_isKfxFmt){S.convHQ=v;}},{0:'4-panel',1:'2-panel',2:'4-panel HQ'},
    _isKfxFmt
      ?t('conv.tip.panel_view_kfx','Panel View is dropped by KFX.\nThe reader takes only the first image of a page, so the magnification markup never reaches the device.')
      :t('conv.tip.panel_view','○ 4 panels — Zoom each corner separately.\n◑ 2 panels — Zoom only top and bottom.\n● 4 HQ panels — Zoom each corner, increased quality.'));
  if(_isKfxFmt)_convDisableControl(_panelEl);
  // MOBI/EPUB native builders consume hq when resolving the device canvas,
  // but never consume autoscale or generate KCC's 2/4-panel zoom markup.
  grid.append(_isNativeFmt&&!_isKfxFmt
    ?mkCheck(t('conv.native_hq','HQ resolution'),S.convHQ===2,v=>{S.convHQ=v?2:0;},
      t('conv.tip.native_hq','Use a 1.5x device canvas before the native render-size minimum is applied. This changes resolution, not Panel View.'))
    :_panelEl);
  grid.append(_gateNative(mkCheck('Webtoon mode',S.convWebtoon,v=>{S.convWebtoon=v;},
    t('conv.tip.webtoon','Enable special parsing mode for Korean Webtoons.'))));
  const _upscaleEl=mkTri('Stretch/Upscale',_isNativeFmt?0:S.convUpscale,
    v=>{if(!_isNativeFmt){S.convUpscale=v;}},{0:'Off',1:'Stretch',2:'Upscale'},
    _isNativeFmt
      ?t('conv.tip.stretch_upscale_kfx','Does not apply to "KFX maic", "MOBI maic" or "EPUB maic": every page is built at a fixed height above the screen and the device reduces it, so there is nothing left to stretch or upscale.')
      :t('conv.tip.stretch_upscale','○ Nothing — Small images not resized.\n◑ Stretching — Resize, aspect ratio NOT preserved.\n● Upscaling — Resize, aspect ratio preserved.'));
  if(_isNativeFmt)_convDisableControl(_upscaleEl);
  grid.append(_upscaleEl);
  grid.append(_gateNative(mkCheck('Custom gamma',S.convGamma>0,v=>{S.convGamma=v?1.8:0;},
    t('conv.tip.custom_gamma','Set a custom gamma correction.\n1.0 = default (disabled). < 1.0 brighter. > 1.0 darker.\n1.8 was the default in KCC 9.1.0 and earlier.'))));
  const _noPadding=_isNativeFmt&&S.convKfxNoPadding;
  const _isMobiMaic=(S.convFormat||'').toUpperCase()==='MOBI MAIC';
  const _isEpubMaic=(S.convFormat||'').toUpperCase()==='EPUB MAIC';
  // MOBI and EPUB both paint this colour in each page's own viewport, so it
  // remains effective with pixel padding disabled. KFX has no such property.
  const _paintsBackground=_isMobiMaic||_isEpubMaic;
  const _wbDisabled=_noPadding&&!_paintsBackground;
  const _wbMarginsEl=mkTri(_paintsBackground?'Page background':'W/B margins',S.convBordersColor==='none'?0:S.convBordersColor==='white'?1:2,
    v=>{if(!_wbDisabled){S.convBordersColor=['none','white','black'][v];}},{0:'Auto',1:'White',2:'Black'},
    _wbDisabled
      ?t('conv.tip.wb_margins_nopad','Disabled while "No padding" is on.\nWithout padded pixels the margin colour cannot be set:\n"KFX maic" has no property that paints the area around a page.')
      :_paintsBackground
        ?t('conv.tip.mobi_background','○ Auto — Detect the background for every source page.\n◑ White — Force a white page viewport.\n● Black — Force a black page viewport.')
        :t('conv.tip.wb_margins','○ Auto — Detect the margin/frame colour automatically.\n◑ White — Force a white frame.\n● Black — Force a black frame.'));
  if(_wbDisabled)_convDisableControl(_wbMarginsEl);
  _wbMarginsEl.style.gridColumn='1';
  _wbMarginsEl.style.gridRow='3';
  const _marginWidthState=((parseInt(S.convAutoBalanceMode)||0)===1)
    ? (((S.convAutoBalanceMarginUnit||'px')==='pct')?2:1)
    : 0;
  const _marginWidthEl=mkTri('Margin width',_marginWidthState,
    v=>{
      if(v===0){
        S.convAutoBalanceMode=0;
        return;
      }
      S.convAutoBalanceMode=1;
      S.convAutoBalanceMarginUnit=(v===2)?'pct':'px';
      if(S.convAutoBalanceMarginUnit==='pct'){
        if((parseFloat(S.convAutoBalanceMarginPct)||0)<=0)S.convAutoBalanceMarginPct=3.0;
      }else{
        if((parseInt(S.convAutoBalanceMarginPx)||0)<=0)S.convAutoBalanceMarginPx=24;
      }
    },
    {0:'Auto',1:'px',2:'%'},
    t('conv.tip.margin_width_mode','○ Auto — Use default KCC W/B margin behaviour.\n◑ px — Fixed side-margin width in pixels after KCC processing.\n● % — Fixed side-margin width as percent of image width after KCC processing.'));
  _marginWidthEl.style.gridColumn='1';
  _marginWidthEl.style.gridRow='4';
  _gateNative(_marginWidthEl);
  grid.append(_wbMarginsEl,_marginWidthEl);
  grid.append(_gateNative(mkTri('Output split',S.convBatchSplit,v=>{S.convBatchSplit=v;},{0:'Off',1:'Auto',2:'Per dir'},
    t('conv.tip.output_split','○ Off — Single output.\n◑ Auto — Output split automatically.\n● Per dir — Every subdirectory is a separate volume.'))));
  grid.append(mkCheck('Color mode',S.convForceColor,v=>{S.convForceColor=v;},
    t('conv.tip.color_mode','Disable conversion to grayscale.')));
  // Native KFX explicitly turns mozjpeg off to retain JPEG restart markers.
  const _jpegTip=t('conv.tip.jpeg_png_mozjpeg','○ JPEG — Use JPEG files.\n◑ force PNG — Create PNG instead of JPEG.\n● mozJpeg — 10–20% smaller, same quality, 2× slower.');
  grid.append(_isNativeFmt&&_isKfxFmt
    ?mkDual('JPEG/PNG',S.convForcePNG===1?1:0,v=>{S.convForcePNG=v;},{0:'JPEG',1:'PNG'},_jpegTip.split('\n').slice(0,2).join('\n'))
    :mkTri('JPEG/PNG/mozJpeg',S.convForcePNG,v=>{S.convForcePNG=v;},{0:'JPEG',1:'PNG',2:'mozJpeg'},_jpegTip));
  grid.append(_gateNative(mkTri('Cropping mode',S.convCropping,v=>{S.convCropping=v;},{0:'Off',1:'Margins',2:'M+Pages'},
    t('conv.tip.cropping_mode','○ Disabled.\n◑ Margins — Crop margins only.\n● Margins + page numbers.'))));
  grid.append(mkCheck(t('conv.maic_crop','maic crop'),S.convMaicCrop,v=>{S.convMaicCrop=v;_invalidateCropCaches();},
    t('conv.tip.maic_crop','Crop safe page margins with the maic algorithm before KCC. The result is shown directly in preview.')));
  grid.append(mkCheck(t('conv.maic_watermarks','Remove watermarks'),S.convMaicWatermarks,v=>{
    S.convMaicWatermarks=v;
    if(!v){S._convWatermarkMenuOpen=false;S._convWatermarkCapture=false;S._convWatermarkDraft=null;S._convWatermarkMessage='';}
    else setTimeout(()=>_convAutoScanWatermarks(S.convSources),0);
    _invalidateCropCaches();
  },t('conv.tip.maic_watermarks','Use your taught watermark samples when calculating the maic crop. Open a page preview to add a sample.')));
  grid.append(mkCheck(t('conv.maic_page_numbers','maic page-number cleanup'),S.convMaicPageNumbers,v=>{
    S.convMaicPageNumbers=v;_invalidateCropCaches();
    S.convPageNumberMatches={};
    if(v)S.convSources.forEach(scope=>_convScanPageNumbers(scope).catch(error=>console.error(error)));
  },
    t('conv.tip.maic_page_numbers','Preview and conversion use local digit recognition with your saved corrections.')));
  const _upscalePassEl=mkTri(t('conv.manga_upscale','Manga upscale'),
    _isNativeFmt?(parseInt(S.convMangaUpscale)||0):0,
    v=>{if(_isNativeFmt){S.convMangaUpscale=v;}},
    {0:t('conv.state.off','Off'),1:t('conv.state.fast','Fast'),2:t('conv.state.exact','Exact')},
    _isNativeFmt
      ?t('conv.tip.manga_upscale','○ Off — ordinary resize to the render height.\n◑ Fast — MangaJaNai 2x, selected for the source height; restores linework and cleans the paper.\n● Exact — Manga Ora 2x only; use Scan cleanup separately when JPEG restoration is needed.\nBoth modes run only on pages below the render height.')
      :t('conv.tip.manga_upscale_off','Only for the "KFX maic", "MOBI maic" or "EPUB maic" format.'));
  if(!_isNativeFmt)_convDisableControl(_upscalePassEl);
  grid.append(_upscalePassEl);
  const _scanCleanupEl=mkCheck(t('conv.scan_cleanup','Scan cleanup'),
    _isNativeFmt?!!S.convScanCleanup:false,
    v=>{if(_isNativeFmt){S.convScanCleanup=v;}},
    _isNativeFmt
      ?t('conv.tip.scan_cleanup','Clean JPEG scan artifacts at 1x after crop and before upscale and resize. The input JPEG quantization table selects HQPlus (81–95), HQ (61–80), MQ (26–60), or LQ (up to 25) automatically. Quality 60 selects MQ. Non-JPEG and quality above 95 stay unchanged. Colour pages keep their colour.')
      :t('conv.tip.scan_cleanup_off','Only for the "KFX maic", "MOBI maic" or "EPUB maic" format.'));
  if(!_isNativeFmt)_convDisableControl(_scanCleanupEl);
  grid.append(_scanCleanupEl);
  const _facingEl=mkCheck(t('conv.facing_pages','Facing pages'),
    _isNativeFmt?!!S.convFacingPages:false,
    v=>{if(_isNativeFmt){S.convFacingPages=v;}},
    _isNativeFmt
      ?(_isEpubMaic
        ?t('conv.tip.facing_pages_epub','Tell the reader which two portrait pages face each other, so a landscape screen shows a spread instead of centring one page.\nPairing follows the source\'s own bisected spreads, so a chapter opens a fresh pair whenever that parity allows; bisected spreads and landscape pages are left alone.\nOff leaves the pairing to the reader.')
        :t('conv.tip.facing_pages','Put two portrait pages in one section, so a landscape screen shows a spread instead of centring one page.\nPairing follows the source\'s own bisected spreads, so a chapter opens a fresh pair whenever that parity allows; bisected spreads and landscape pages are left alone.'))
      :t('conv.tip.facing_pages_off','Only for the "KFX maic", "MOBI maic" or "EPUB maic" format.'));
  if(!_isNativeFmt)_convDisableControl(_facingEl);
  grid.append(_facingEl);
  const _seamFmt=_seamFormat(S.convFormat);
  const _forceSpreadPreviewEl=mkTri(t('conv.force_spread_preview','Spread preview'),
    _seamFmt?(parseInt(S.convSpreadPreviewMode)||0):0,
    v=>{if(_seamFmt){S.convSpreadPreviewMode=v;}},
    {0:t('conv.state.off','Off'),1:t('conv.state.auto','Auto'),2:t('conv.state.always','Always')},
    _seamFmt
      ?t('conv.tip.force_spread_preview','○ Off — leave every split unchanged.\n◑ Auto — inspect ink and continuity at the fold, and match one pixel only when Kindle is unlikely to offer Preview Double Page Spread on its own.\n● Always — match one pixel on every split spread.\nOnly source spreads that maic bisects are considered; ordinary facing pages and source files stay unchanged. EPUB reaches Kindle through Send-to-Kindle as KFX.')
      :t('conv.tip.force_spread_preview_off','Only for the "KFX maic" and "EPUB maic" formats.'));
  if(!_seamFmt)_convDisableControl(_forceSpreadPreviewEl);
  grid.append(_forceSpreadPreviewEl);
  grid.append(_gateNative(mkCheck('Spread shift',S.convSpreadShift,v=>{S.convSpreadShift=v;},
    t('conv.tip.spread_shift','Shift first page to opposite side in landscape for two page spread alignment.'))));
  grid.append(_gateNative(mkCheck('Match spread width',S.convMatchSpreadWidth,v=>{S.convMatchSpreadWidth=v;},
    t('conv.tip.match_spread_width','Pad single-page images to match the width of spread halves.\nEnsures uniform visual width across all pages.'))));
  grid.append(_gateNative(mkCheck('Screen side margins',S.convScreenMargins,v=>{S.convScreenMargins=v;},
    t('conv.tip.screen_margins','Add 3% side margins to images that reach the screen width.\nPrevents content from touching the edges of the device screen.'))));
  const _paddingStates={
    0:t('conv.state.padding','Padding'),
    1:t('conv.state.no_padding','No padding')
  };
  const _noPadEl=mkDual(t('conv.page_padding','Page padding'),S.convKfxNoPadding?1:0,
    v=>{if(_isNativeFmt){S.convKfxNoPadding=v===1;}},_paddingStates,
    _isNativeFmt
      ?(_paintsBackground
        ?t('conv.tip.mobi_padding_states','○ Padding — Fit each ordinary page to the shared canvas; missing area is added as image pixels using Page background.\n● No padding — Keep the page proportions and add no margin pixels; Page background paints the free viewport area.\nThe cover and split-spread halves are never padded in either state.')
        :t('conv.tip.kfx_padding_states','○ Padding — Fit each ordinary page to the shared canvas and bake margin pixels into the image.\n● No padding — Keep the page proportions and add no margin pixels; free screen area remains white.\nThe cover and split-spread halves are never padded in either state.'))
      :t('conv.tip.kfx_no_padding_off','Only for the "KFX maic", "MOBI maic" or "EPUB maic" format.'));
  if(!_isNativeFmt)_convDisableControl(_noPadEl);
  grid.append(_noPadEl);
  grid.append(_gateNative(mkTri('Autocontrast',S.convNoAutocontrast?1:S.convColorAutocontrast?2:0,
    v=>{S.convNoAutocontrast=(v===1);S.convColorAutocontrast=(v===2);},{0:'BW only',1:'Off',2:'BW+Color'},
    t('conv.tip.autocontrast','○ BW only — Autocontrast BW pages. Ignored where near blacks/whites absent.\n◑ Disabled.\n● BW and Color — Both BW and color images autocontrasted.'))));
  grid.append(_gateNative(mkTri('Metadata Title',S.convMetadataTitle||0,v=>{S.convMetadataTitle=v;},{0:'Default',1:'Combine',2:'Title only'},
    t('conv.tip.metadata_title',"○ Don't use metadata Title — Write default title.\n◑ Combine — Default title + metadata from ComicInfo.xml.\n● Title only — Use Title from ComicInfo.xml."))));
  grid.append(_gateNative(mkCheck('Extreme Black Point',S.convAutolevel>0,v=>{S.convAutolevel=v?1:0;},
    t('conv.tip.extreme_black','Maps darkest pixel to pure black.\nUseful when text is black but artwork is gray.'))));
  grid.append(mkCheck('Custom JPEG Quality',S.convCustomJpeg,v=>{S.convCustomJpeg=v;},
    t('conv.tip.custom_jpeg_quality','Override default JPEG compression quality.\nSlider appears below when checked.')));
  grid.append(_gateNative(mkCheck('Rainbow eraser',S.convEraseRainbow,v=>{S.convEraseRainbow=v;},
    t('conv.tip.rainbow_eraser','Erase rainbow effect on color e-ink screen by attenuating interfering frequencies.'))));
  body.append(grid);

  // Conditional sub-controls - unified slider style (50% width grid)
  const subControls=h('div',{style:{marginTop:'0.7rem',paddingTop:'0.6rem',borderTop:'1px solid var(--glass-border)',
    display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.6rem 1rem'}});
  const _mkSlider=(label,value,min,max,step,fmt,onSet)=>{
    const div=h('div',{});
    const row=h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.3rem'}});
    row.append(h('span',{className:'conv-field-label',style:{margin:0}},label));
    const valSpan=h('span',{style:{fontSize:'0.72rem',fontFamily:'var(--font-mono)',color:'var(--accent)',fontWeight:'700'}},fmt(value));
    row.append(valSpan);div.append(row);
    div.append(h('input',{type:'range',min:String(min),max:String(max),step:String(step),value:String(value),
      style:{width:'100%',accentColor:'var(--accent)'},
      onInput:e=>{onSet(e.target.value);valSpan.textContent=fmt(e.target.value);},
      onChange:()=>{render();}}));
    return div;
  };
  const _mkSpin=(label,value,min,max,unit,onSet)=>{
    const div=h('div',{});
    div.append(h('div',{className:'conv-field-label',style:{marginBottom:'0.3rem'}},label+(unit?' ('+unit+')':'')));
    const wrap=h('div',{style:{display:'flex',alignItems:'center',gap:'0.3rem'}});
    const bst={width:'1.6rem',height:'1.6rem',display:'flex',alignItems:'center',justifyContent:'center',
      background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'8px',color:'var(--text2)',
      cursor:'pointer',fontSize:'0.85rem',fontWeight:'500',transition:'all .15s',padding:0,lineHeight:1};
    const inp=h('input',{type:'text',inputMode:'numeric',value:String(value),
      style:{width:'3rem',background:'var(--glass)',border:'1px solid var(--glass-border)',borderRadius:'8px',
        padding:'0.3rem 0.2rem',fontSize:'0.78rem',color:'var(--accent)',fontFamily:'var(--font-mono)',fontWeight:'700',
        outline:'none',textAlign:'center',transition:'border-color .2s'},
      onFocus:function(){this.style.borderColor='var(--accent)';},
      onBlur:function(){this.style.borderColor='var(--glass-border)';let v=parseInt(this.value)||min;v=Math.max(min,Math.min(max,v));this.value=v;onSet(v);},
      onInput:e=>{let v=parseInt(e.target.value);if(!isNaN(v))onSet(Math.max(min,Math.min(max,v)));},
      onKeydown:e=>{if(e.key==='Enter')e.target.blur();}});
    wrap.append(h('button',{style:{...bst},onClick:()=>{const v=Math.max(min,(parseInt(inp.value)||0)-1);inp.value=v;onSet(v);render();},
      onMouseover:function(){this.style.borderColor='var(--accent)';this.style.color='var(--accent)';},
      onMouseout:function(){this.style.borderColor='var(--glass-border)';this.style.color='var(--text2)';}},'-'));
    wrap.append(inp);
    wrap.append(h('button',{style:{...bst},onClick:()=>{const v=Math.min(max,(parseInt(inp.value)||0)+1);inp.value=v;onSet(v);render();},
      onMouseover:function(){this.style.borderColor='var(--accent)';this.style.color='var(--accent)';},
      onMouseout:function(){this.style.borderColor='var(--glass-border)';this.style.color='var(--text2)';}},'+'));
    div.append(wrap);return div;
  };
  if(!_isNativeFmt&&S.convGamma>0){
    subControls.append(_mkSlider('Gamma',S.convGamma,0.1,4.0,0.1,
      v=>String(parseFloat(v)),v=>{S.convGamma=parseFloat(v);S.convGammaAuto=false;}));
  }
  if(!_isNativeFmt&&S.convCropping>0){
    subControls.append(_mkSlider('Cropping Power',S.convCroppingPower,0.0,3.0,0.1,
      v=>'Level '+parseFloat(v),v=>{S.convCroppingPower=parseFloat(v);}));
    const pmRow=h('div',{style:{display:'flex',gap:'0.7rem',alignItems:'flex-start'}});
    pmRow.append(_mkSpin('Preserve Margin H',S.convPreserveMarginH||0,0,100,'%',v=>{S.convPreserveMarginH=v;}));
    pmRow.append(_mkSpin('Preserve Margin V',S.convPreserveMarginV||0,0,100,'%',v=>{S.convPreserveMarginV=v;}));
    subControls.append(pmRow);
  }
  if(S.convMaicCrop){
    subControls.append(_mkSlider(t('conv.maic_margin_pct','maic preserved margin'),parseFloat(S.convMaicMarginPct)||0,0,10,0.1,
      v=>`${(Math.round((parseFloat(v)||0)*10)/10).toFixed(1)} %`,
      v=>{S.convMaicMarginPct=Math.max(0,Math.min(10,parseFloat(v)||0));_invalidateCropCaches();}));
  }
  if(S.convCustomJpeg){
    subControls.append(_mkSlider('JPEG Quality',S.convJpegQ,10,100,1,
      v=>String(parseInt(v)),v=>{S.convJpegQ=parseInt(v)||85;}));
  }
  if(!_isNativeFmt&&(parseInt(S.convAutoBalanceMode)||0)===1){
    if((S.convAutoBalanceMarginUnit||'px')==='pct'){
      subControls.append(_mkSlider('Margin width',parseFloat(S.convAutoBalanceMarginPct)||0,0,20,0.1,
        v=>`${(Math.round((parseFloat(v)||0)*10)/10).toFixed(1)} %`,
        v=>{S.convAutoBalanceMarginPct=Math.max(0,Math.min(100,parseFloat(v)||0));}));
    }else{
      subControls.append(_mkSlider('Margin width',parseInt(S.convAutoBalanceMarginPx)||0,0,400,1,
        v=>`${parseInt(v,10)||0} px`,v=>{S.convAutoBalanceMarginPx=parseInt(v,10)||0;}));
    }
  }
  if(subControls.children.length>0)body.append(subControls);
  });

  // Encoding-normalized comment.
  mkAccordion('advanced','\ud83d\udcc2','rgba(251,146,60,0.12)',
    t('conv.sec_advanced'),t('conv.sec_advanced_sub'),body=>{

  const mkCheck2=(label,val,setter,tip)=>{
    const key=label;label=_convOptionText(label);
    const lb=h('label',{className:'conv-check'});
    const state=val?t('conv.state.on','On'):t('conv.state.off','Off');
    if(tip)lb.setAttribute('data-tip',_stateTip(tip,val?'●':'○',state));
    const cb=h('input',{type:'checkbox','data-focus-key':'conv-'+key});cb.checked=val;
    cb.addEventListener('change',e=>{setter(e.target.checked);render();});
    lb.append(cb,label,_stateSpan(state));return lb;
  };

  const mkState2=(label,val,setter,states,tip,marker,toNext)=>{
    const key=label;label=_convOptionText(label);
    const lb=h('label',{className:'conv-check'});
    const state=_convOptionText(states[val]||String(val));
    if(tip)lb.setAttribute('data-tip',_stateTip(tip,marker,state));
    const cb=h('input',{type:'checkbox','data-focus-key':'conv-'+key});
    cb.checked=val>0;cb.indeterminate=(marker==='◑');
    cb.addEventListener('click',e=>{e.preventDefault();setter(toNext(val));render();});
    lb.append(cb,label,_stateSpan(state));
    return lb;
  };
  const mkTri2=(label,val,setter,states,tip)=>
    mkState2(label,val,setter,states,tip,['○','◑','●'][val]||'○',v=>(v+1)%3);
  const mkDual2=(label,val,setter,states,tip)=>
    mkState2(label,val,setter,states,tip,val===1?'●':'○',v=>(v===1?0:1));

  const grid2=h('div',{className:'conv-grid'});
  grid2.append(_gateNative(mkCheck2('Delete input',S.convDeleteInput,v=>{S.convDeleteInput=v;},
    t('conv.tip.delete_input','⚠ Delete input file(s) or directory. Not recoverable!'))));
  grid2.append(mkCheck2('Disable processing',S.convNoProcessing,v=>{S.convNoProcessing=v;},
    t('conv.tip.disable_processing','Do not process any image, ignore profile and processing options.')));
  grid2.append(_gateNative(mkCheck2('File Fusion',S.convFileFusion,v=>{S.convFileFusion=v;},
    t('conv.tip.file_fusion','Combines all selected files into a single file.\nHelpful for combining chapters into volumes.'))));
  const _docTypeEl=mkDual2('Kindle doc type',S.convKindleDocType==='pdoc'?1:0,
    v=>{S.convKindleDocType=v===1?'pdoc':'ebok';},{0:'EBOK',1:'PDOC'},
    t('conv.tip.kindle_doc_type','Set Kindle metadata doc type for MOBI/KFX output.\nOff: EBOK — Book type.\nOn: PDOC — Personal document.'));
  if((S.convFormat||'').toUpperCase()==='EPUB MAIC')_convDisableControl(_docTypeEl);
  grid2.append(_docTypeEl);
  grid2.append(mkCheck2('No rotate',S.convNoRotate,v=>{S.convNoRotate=v;},
    t('conv.tip.no_rotate','Do not rotate double page spreads.\nKCC formats: the spread splitter leaves a spread as it is instead of turning it.\nmaic formats: a panorama too wide to bisect is cut in half like any other spread.')));
  grid2.append(_gateNative(mkCheck2('Rotate First',S.convRotateFirst,v=>{S.convRotateFirst=v;},
    t('conv.tip.rotate_first','When spread splitter is active:\n○ Rotate Last — Rotated spread after split pages.\n● Rotate First — Rotated spread before split pages.'))));
  grid2.append(_gateNative(mkCheck2('Chunk size',S.convChunkSize>0,v=>{S.convChunkSize=v?195:0;render();},
    t('conv.tip.chunk_size','Split output into chunks of target size.\nDefault: 195 MB. Range: 100–600 MB.'))));
  grid2.append(_gateNative(mkCheck2('PDF Legacy Extract',S.convPdfLegacy,v=>{S.convPdfLegacy=v;},
    t('conv.tip.pdf_legacy','Use legacy PDF image extraction method.'))));
  grid2.append(_gateNative(mkTri2('Inter-panel crop',S.convInterPanelCrop,v=>{S.convInterPanelCrop=v;},{0:'Off',1:'Horiz',2:'Both'},
    t('conv.tip.inter_panel_crop','○ Disabled.\n◑ Horizontal — Crop empty horizontal lines.\n● Both — Crop empty horizontal and vertical lines.'))));
  body.append(grid2);

  // Chunk size slider
  if(!_isNativeFmt&&S.convChunkSize>0){
    const csDiv=h('div',{style:{marginTop:'0.7rem',paddingTop:'0.6rem',borderTop:'1px solid var(--glass-border)'}});
    const csRow=h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.3rem'}});
    csRow.append(h('span',{className:'conv-field-label',style:{margin:0}},'Target Size'));
    const csVal=h('span',{style:{fontSize:'0.72rem',fontFamily:'var(--font-mono)',color:'var(--accent)',fontWeight:'700'}},S.convChunkSize+' MB');
    csRow.append(csVal);csDiv.append(csRow);
    csDiv.append(h('input',{type:'range',min:'100',max:'600',step:'5',value:String(S.convChunkSize),
      style:{width:'100%',accentColor:'var(--accent)'},
      onInput:e=>{S.convChunkSize=parseInt(e.target.value);csVal.textContent=S.convChunkSize+' MB';},
      onChange:()=>{render();}}));
    body.append(csDiv);
  }

  // Per-source crop data sections
  S.convSources.forEach(src=>{
    const files=S.convScanned[src]||[];
    const relPaths=new Set(files.map(f=>f.relPath));
    const srcNC=Object.entries(S.convExclusions).filter(([k,v])=>v['no-crop']&&relPaths.has(k));
    const srcCC=Object.entries(S.convCustomCrop).filter(([k])=>relPaths.has(k));
    const srcEX=Object.entries(S.convExcluded).filter(([k])=>relPaths.has(k));
    const srcEM=Object.entries(S.convExtraMargin).filter(([k,v])=>relPaths.has(k)&&(v.top||v.bottom||v.left||v.right));
    const srcEO=Object.entries(S.convEditOps).filter(([k,v])=>relPaths.has(k)&&v&&v.length);
    const normRelPaths=new Set(files.map(f=>_convNormPath(f.relPath)));
    const srcWM=(S.convMaicWatermarks?Object.keys((S.convWatermarkMatches&&S.convWatermarkMatches[src])||{}):[])
      .filter(name=>normRelPaths.has(_convNormPath(name)));
    if(srcNC.length===0&&srcCC.length===0&&srcEX.length===0&&srcEM.length===0&&srcEO.length===0&&srcWM.length===0)return;
    const srcName=src.split(/[/\\]/).filter(Boolean).slice(-1)[0];
    const sKey='_cropOpen_'+src;
    if(S[sKey]===undefined)S[sKey]=true;
    const cropDiv=h('div',{style:{marginTop:'0.5rem',paddingTop:'0.5rem',borderTop:'1px solid var(--glass-border)'}});
    // Header row: collapsible title + save/load/clear
    const titleRow=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:S[sKey]?'0.35rem':'0'}});
    const titleLeft=h('div',{style:{display:'flex',alignItems:'center',gap:'0.35rem',cursor:'pointer',flex:'1',minWidth:0},
      onClick:()=>{S[sKey]=!S[sKey];render();}});
    titleLeft.append(h('span',{style:{fontSize:'0.55rem',color:'var(--text3)',transition:'transform .2s',transform:S[sKey]?'rotate(90deg)':'rotate(0deg)'}},'\u25B6'));
    titleLeft.append(h('span',{className:'conv-field-label',style:{margin:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},
      srcName+' ('+[srcEX.length?srcEX.length+' \u2715':'',srcNC.length?srcNC.length+' \u2298':'',srcCC.length?srcCC.length+' \u2702':'',srcEM.length?srcEM.length+' +M':'',srcEO.length?srcEO.length+' \u270E':'',srcWM.length?'\u25C7 Watermark':''].filter(Boolean).join(', ')+')'));
    titleRow.append(titleLeft);
    const btns=h('div',{style:{display:'flex',gap:'0.25rem',alignItems:'center',flexShrink:0}});
    const _bs={background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'6px',
      padding:'0.1rem 0.35rem',cursor:'pointer',color:'var(--text3)',fontSize:'0.55rem',transition:'all .2s',display:'flex',alignItems:'center',gap:'0.15rem'};
    // Save this source
    btns.append(h('button',{style:{..._bs},
      onClick:async()=>{
        if(await _convSaveSidecarForSource(src)){
          S.status='\ud83d\udcbe '+srcName+'.sidecar.json \u2713';render();
        }
      },
      onMouseover:function(){this.style.color='var(--accent)';},
      onMouseout:function(){this.style.color='var(--text3)';},
      title:t('conv.crop_save_tip','Save')},'\ud83d\udcbe'));
    // Load for this source
    btns.append(h('button',{style:{..._bs},
      onClick:async()=>{
        const br=await(await apiPost('/api/browse-json',{})).json();
        if(!br.ok||!br.path)return;
        const r=await(await apiPost('/api/crop-sidecar/load',{path:br.path})).json();
        if(!r.ok){alert(r.error);return;}
        (r['no-crop']||[]).forEach(k=>{if(relPaths.has(k))S.convExclusions[k]={'no-crop':true};});
        Object.entries(r['custom-crop']||{}).forEach(([k,v])=>{if(relPaths.has(k))S.convCustomCrop[k]=v;});
        (r['excluded']||[]).forEach(k=>{if(relPaths.has(k))S.convExcluded[k]=true;});
        Object.entries(r['extra-margin']||{}).forEach(([k,v])=>{if(relPaths.has(k)){S.convExtraMargin[k]=v;}});
        Object.entries(r['edit-ops']||{}).forEach(([k,v])=>{if(relPaths.has(k)&&Array.isArray(v)&&v.length)S.convEditOps[k]=v;});
        const detected={};(r['watermark-matches']||[]).forEach(k=>{const rel=_convNormPath(k);if(normRelPaths.has(rel))detected[rel]=1;});
        S.convWatermarkMatches={...(S.convWatermarkMatches||{}),[src]:detected};
        S.convWatermarkReviewed={...(S.convWatermarkReviewed||{}),[src]:!!r['watermark-matches-saved']};
        _invalidateCropCaches();render();
      },
      onMouseover:function(){this.style.color='var(--accent)';},
      onMouseout:function(){this.style.color='var(--text3)';},
      title:t('conv.crop_load_tip','Load')},'\ud83d\udcc2'));
    // Clear this source
    btns.append(h('button',{style:{background:'var(--glass2)',border:'1px solid var(--glass-border)',borderRadius:'50%',
      width:'1.2rem',height:'1.2rem',display:'flex',alignItems:'center',justifyContent:'center',cursor:'pointer',color:'var(--text3)',transition:'all .2s',flexShrink:0},
      onClick:()=>{
        files.forEach(f=>{if(f.relPath){delete S.convExclusions[f.relPath];delete S.convCustomCrop[f.relPath];delete S.convCustomSplit[f.relPath];delete S.convExcluded[f.relPath];delete S.convExtraMargin[f.relPath];delete S.convEditOps[f.relPath];}});
        S.convWatermarkMatches={...(S.convWatermarkMatches||{}),[src]:{}};
        S.convWatermarkReviewed={...(S.convWatermarkReviewed||{}),[src]:true};
        _invalidateCropCaches();render();
      },
      onMouseover:function(){this.style.color='var(--red)';},
      onMouseout:function(){this.style.color='var(--text3)';},
      innerHTML:'<svg width="8" height="8" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'}));
    titleRow.append(btns);
    cropDiv.append(titleRow);
    // Collapsible tags
    if(S[sKey]){
      const tagGrid=h('div',{style:{display:'flex',flexWrap:'wrap',gap:'0.2rem'}});
      srcNC.forEach(([name])=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'var(--orange)',background:'var(--orange-bg)',border:'1px solid rgba(251,146,60,0.2)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          onClick:()=>{delete S.convExclusions[name];render();}});
        tag.append(h('span',{},'\u2298 '+name));tag.append(h('span',{style:{opacity:'0.5'}},'\u2715'));
        tagGrid.append(tag);
      });
      srcCC.forEach(([name])=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'var(--accent)',background:'rgba(110,170,255,0.08)',border:'1px solid rgba(110,170,255,0.2)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          onClick:()=>{delete S.convCustomCrop[name];_invalidateCropCaches();render();}});
        tag.append(h('span',{},'\u2702 '+name));tag.append(h('span',{style:{opacity:'0.5'}},'\u2715'));
        tagGrid.append(tag);
      });
      srcEX.forEach(([name])=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'var(--red)',background:'rgba(248,113,113,0.08)',border:'1px solid rgba(248,113,113,0.2)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          onClick:()=>{delete S.convExcluded[name];render();}});
        tag.append(h('span',{},'\u2715 '+name));tag.append(h('span',{style:{opacity:'0.5'}},'\u2715'));
        tagGrid.append(tag);
      });
      srcEM.forEach(([name])=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'rgb(34,197,94)',background:'rgba(34,197,94,0.08)',border:'1px solid rgba(34,197,94,0.2)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          onClick:()=>{delete S.convExtraMargin[name];_invalidateCropCaches();render();}});
        tag.append(h('span',{},'+M '+name));tag.append(h('span',{style:{opacity:'0.5'}},'\u2715'));
        tagGrid.append(tag);
      });
      srcEO.forEach(([name])=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'var(--orange)',background:'rgba(251,146,60,0.08)',border:'1px solid rgba(251,146,60,0.2)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          onClick:()=>{delete S.convEditOps[name];render();}});
        tag.append(h('span',{},'\u270E '+name));tag.append(h('span',{style:{opacity:'0.5'}},'\u2715'));
        tagGrid.append(tag);
      });
      srcWM.forEach(name=>{
        const tag=h('span',{style:{display:'inline-flex',alignItems:'center',gap:'0.2rem',
          fontSize:'0.6rem',color:'#facc15',background:'rgba(234,179,8,0.12)',border:'1px solid rgba(250,204,21,0.32)',
          borderRadius:'var(--radius-xs)',padding:'0.1rem 0.35rem',cursor:'pointer'},
          title:t('conv.watermark_remove_page_tip','Do not treat this detection as a watermark on this page'),
          onClick:()=>_convRemoveWatermark(src,name)});
        tag.append(h('span',{},'\u25C7 '+t('conv.watermark_badge','Watermark')+' · '+name));
        tag.append(h('span',{style:{opacity:'0.55'}},'\u2715'));
        tagGrid.append(tag);
      });
      cropDiv.append(tagGrid);
    }
    body.append(cropDiv);
  });
  });

  // Encoding-normalized comment.
  if(cs.converting||cs.log&&cs.log.length>0||cs.output_files&&cs.output_files.length>0){
    const acc=h('div',{className:'conv-accordion',style:{marginBottom:'0.8rem'}});

    // Header
    const hdr=h('div',{className:'conv-accordion-hdr',style:{cursor:'default'}});
    const hLeft=h('div',{className:'conv-accordion-left'});
    const _presentation=_convStatusPresentation(cs);
    const _isDone=_presentation.done;
    const icon=h('div',{className:'conv-accordion-icon',style:{background:_isDone?'rgba(34,197,94,0.15)':'rgba(99,102,241,0.15)',fontSize:'1rem',color:_presentation.color}},_presentation.icon);
    const hText=h('div');
    hText.append(h('div',{className:'conv-accordion-title',style:{color:_presentation.color}},_presentation.label));
    const _subText=cs.converting?_convStatusDetail(cs):
      cs.output_files&&cs.output_files.length?`${t('conv.created_files','Created files')}: ${cs.output_files.length}`:_presentation.label;
    const hSub=h('div',{id:'convInfo',className:'conv-accordion-sub'},_subText);
    hText.append(hSub);
    hLeft.append(icon,hText);
    hdr.append(hLeft);
    // Encoding-normalized comment.
    const pctEl=h('span',{id:'tbProgressPct2',style:{fontSize:'0.78rem',fontWeight:'700',color:'var(--accent)'}},
      cs.converting?(cs.progress||0)+'%':'');
    hdr.append(pctEl);
    acc.append(hdr);

    // Body
    const body=h('div',{className:'conv-accordion-body'});

    // Encoding-normalized comment.
    if(cs.converting){
      const pbar=h('div',{style:{height:'4px',background:'var(--glass2)',borderRadius:'4px',overflow:'hidden',marginBottom:'0.6rem'}});
      pbar.append(h('div',{id:'convBar',style:{height:'100%',width:(cs.progress||0)+'%',
        background:'linear-gradient(90deg,var(--accent),var(--accent2))',borderRadius:'4px',transition:'width .4s ease'}}));
      body.append(pbar);
    }

    // Encoding-normalized comment.
    if(cs.output_files&&cs.output_files.length>0){
      cs.output_files.forEach(f=>{
        body.append(h('div',{style:{fontSize:'0.7rem',color:'var(--green)',padding:'0.15rem 0'}},
          '\u2705 '+f.split(/[/\\]/).slice(-1)[0]));
      });
    }

    // Encoding-normalized comment.
    if(cs.converting||(cs.log&&cs.log.length>0)){
      // Encoding-normalized comment.
      const logHdr=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginTop:'0.5rem',marginBottom:'0.2rem'}});
      logHdr.append(h('span',{style:{fontSize:'0.6rem',fontWeight:'600',color:'var(--text3)',textTransform:'uppercase',letterSpacing:'0.6px'}},t('conv.log','Log')));
      const logBtns=h('div',{style:{display:'flex',gap:'0.3rem'}});
      const advBtn=h('button',{style:{fontSize:'0.6rem',color:S.convAdvancedLog?'var(--accent)':'var(--text3)',background:'none',border:'none',cursor:'pointer',padding:'0.1rem 0.3rem',borderRadius:'4px',transition:'color .15s'},
        title:'Toggle detailed converter log',
        onMouseover:function(){this.style.color=S.convAdvancedLog?'var(--accent)':'var(--text)';},
        onMouseout:function(){this.style.color=S.convAdvancedLog?'var(--accent)':'var(--text3)';},
        onClick:async()=>{
          try{
            const next=!S.convAdvancedLog;
            const r=await (await apiPost('/api/convert/log-mode',{advanced:next})).json();
            if(r&&r.ok){
              S.convAdvancedLog=!!r.advanced_log;
              localStorage.setItem('mcs_convAdvancedLog', S.convAdvancedLog?'true':'false');
              if(S.convPollId) await pollConvertStatus();
              render();
            }
          }catch(e){}
        }},S.convAdvancedLog?'Advanced: ON':'Advanced: OFF');
      logBtns.append(advBtn);
      const copyBtn=h('button',{style:{fontSize:'0.6rem',color:'var(--text3)',background:'none',border:'none',cursor:'pointer',padding:'0.1rem 0.3rem',borderRadius:'4px',transition:'color .15s'},
        onMouseover:function(){this.style.color='var(--text)';},
        onMouseout:function(){this.style.color='var(--text3)';},
        onClick:()=>{
          const el=document.getElementById('convLog');
          if(!el)return;
          const text=[...el.children].map(d=>d.textContent).join('\n');
          navigator.clipboard.writeText(text).then(()=>{copyBtn.textContent='✓ '+t('ui.copied','Copied');setTimeout(()=>{copyBtn.textContent='⎘ '+t('ui.copy','Copy');},1500);});
        }},'⎘ '+t('ui.copy','Copy'));
      logBtns.append(copyBtn);
      if(!cs.converting){
        const clearBtn=h('button',{style:{fontSize:'0.6rem',color:'var(--text3)',background:'none',border:'none',cursor:'pointer',padding:'0.1rem 0.3rem',borderRadius:'4px',transition:'color .15s'},
          onMouseover:function(){this.style.color='var(--red)';},
          onMouseout:function(){this.style.color='var(--text3)';},
          onClick:()=>{S.convStatus.log=[];S.convStatus.output_files=[];render();}},'✕ '+t('ui.clear','Clear'));
        logBtns.append(clearBtn);
      }
      logHdr.append(logBtns);
      body.append(logHdr);
      const logDiv=h('div',{className:'conv-log',id:'convLog'});
      if(Array.isArray(cs.log))cs.log.forEach(line=>{const d=document.createElement('div');d.textContent=line;logDiv.append(d);});
      body.append(logDiv);
      requestAnimationFrame(()=>{const el=document.getElementById('convLog');if(el)el.scrollTop=el.scrollHeight;});
    }

    acc.append(body);
    settings.append(acc);
  }

  ca.append(settings);

  // Restore scroll position
  requestAnimationFrame(()=>{
    const ca2=document.querySelector('.canvas-area');
    if(ca2&&S._convCanvasScroll!=null){ca2.scrollTop=S._convCanvasScroll;}
  });
  } // end settings mode
  main.append(ca);

  main.append(_convRenderStatusBar());

  body.append(main);
  app.append(body);
}


// Encoding-normalized comment.
const _tipIcons={
  'в—‹':'<svg width="14" height="14" viewBox="0 0 16 16" style="vertical-align:-2px;margin-right:3px"><rect x="1" y="1" width="14" height="14" rx="3" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/></svg>',
  'в—‘':'<svg width="14" height="14" viewBox="0 0 16 16" style="vertical-align:-2px;margin-right:3px"><rect x="1" y="1" width="14" height="14" rx="3" fill="rgba(96,165,250,0.15)" stroke="rgba(96,165,250,0.7)" stroke-width="1.5"/><rect x="4" y="6" width="8" height="2.5" rx="1" fill="rgba(96,165,250,0.8)"/></svg>',
  'в—Џ':'<svg width="14" height="14" viewBox="0 0 16 16" style="vertical-align:-2px;margin-right:3px"><rect x="1" y="1" width="14" height="14" rx="3" fill="rgba(96,165,250,0.25)" stroke="rgba(96,165,250,0.8)" stroke-width="1.5"/><path d="M4.5 8L7 10.5L11.5 5.5" fill="none" stroke="rgba(96,165,250,1)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};
function _tipHtml(text){
  return text.replace(/\n/g,'<br>').replace(/[в—‹в—‘в—Џ]/g,m=>_tipIcons[m]||m);
}
let _tipEl=null,_tipTimer=null;
document.addEventListener('mouseover',e=>{
  const el=e.target.closest('[data-tip]');
  if(!el){if(_tipEl){_tipEl.remove();_tipEl=null;}clearTimeout(_tipTimer);return;}
  clearTimeout(_tipTimer);
  _tipTimer=setTimeout(()=>{
    if(_tipEl)_tipEl.remove();
    _tipEl=document.createElement('div');
    _tipEl.className='kcc-tip';
    _tipEl.innerHTML=_tipHtml(el.dataset.tip);
    document.body.append(_tipEl);
    const r=el.getBoundingClientRect();
    let left=r.left, top=r.bottom+6;
    if(left+_tipEl.offsetWidth>window.innerWidth-8)left=window.innerWidth-_tipEl.offsetWidth-8;
    if(left<4)left=4;
    if(top+_tipEl.offsetHeight>window.innerHeight-8)top=r.top-_tipEl.offsetHeight-6;
    _tipEl.style.left=left+'px';
    _tipEl.style.top=top+'px';
  },350);
});
document.addEventListener('mouseout',e=>{
  const el=e.target.closest('[data-tip]');
  if(el){clearTimeout(_tipTimer);if(_tipEl){_tipEl.remove();_tipEl=null;}}
});

let _convResizeTimer=null;
let _convResizeRaf=0;
window.addEventListener('resize',()=>{
  const ca=document.querySelector('.canvas-area');
  if(ca){
    S._convCanvasW=ca.clientWidth||0;
    S._convCanvasH=ca.clientHeight||0;
  }
  if(typeof _convLiveSync==='function'){
    if(_convResizeRaf)cancelAnimationFrame(_convResizeRaf);
    _convResizeRaf=requestAnimationFrame(()=>{if(typeof _convLiveSync==='function')_convLiveSync();});
  }
  if(S.tab!=='convert'||S.convViewIdx===null||_convUsesFinalPreview())return;
  clearTimeout(_convResizeTimer);
  _convResizeTimer=setTimeout(()=>{
    const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
    const file=(Array.isArray(sc)&&S.convViewIdx>=0&&S.convViewIdx<sc.length)?sc[S.convViewIdx]:null;
    if(!file)return;
    const order=_convGetSplitOrderForFile(file);
    const autoSel=String(S.convPreviewVariant||'auto').toLowerCase()==='auto';
    const splitPairMode=_convEffectiveSplitter()!==1;
    if(!(splitPairMode&&autoSel&&order.length>1))return;
    const splitStep=_convGetSplitStep(file.relPath,order.length);
    const pairRange=_convCanShowSplitPairForOrder(order,file)?_convGetPairRange(order,splitStep):null;
    const shouldPair=!!pairRange;
    const isPair=!!document.querySelector('.conv-pair-stage');
    if(shouldPair!==isPair)render();
  },140);
});

// Init
checkBackend();render();
// Restore sources from sessionStorage
if(S.cleanSources.length>0)loadCleanSources();
// Restore in-progress batch operation after page reload
pollBatch();
// Restore autonomous operation after page reload
pollAutonomous();

// Load folder from path (shared helper)
async function loadFolderByPath(folderPath){
  try{
    if(!S.cleanSources.includes(folderPath)){S.cleanSources.push(folderPath);}
    await loadCleanSources();
  }catch(e){alert(t('clean.error','Error: ')+e.message);}
}

document.addEventListener('keydown',e=>{
  // Close settings with Esc (global)
  if(e.key==='Escape'&&S.showSettings){e.preventDefault();S.showSettings=false;render();setTimeout(loadCurrentImage,30);return;}
  // Convert tab viewer
  if(S.tab==='convert'&&S.convViewIdx!==null){
    const sc=S.convExpandedSource?S.convScanned[S.convExpandedSource]:null;
    const cvf=sc&&S.convViewIdx>=0?sc[S.convViewIdx]:null;
    // Encoding-normalized comment.
    const _ae=document.activeElement;
    if(_ae&&(_ae.tagName==='INPUT'||_ae.tagName==='TEXTAREA')){
      if(e.key==='Escape'){_ae.blur();S._convBookmarkEdit=false;render();}
      return;
    }
    if(e.key==='Escape'&&(S._convWatermarkMenuOpen||S._convWatermarkCapture||S._convWatermarkDraft)){
      e.preventDefault();S._convWatermarkMenuOpen=false;S._convWatermarkCapture=false;S._convWatermarkDraft=null;S._convWatermarkMessage='';render();return;
    }
    if(e.key==='Escape'){e.preventDefault();S.convViewIdx=null;convResetView();render();return;}
    if((e.key==='ArrowLeft'||e.key==='a'||e.key==='ф')&&_convNavigatePreview(-1)){e.preventDefault();return;}
    if((e.key==='ArrowRight'||e.key==='d'||e.key==='в')&&_convNavigatePreview(1)){e.preventDefault();return;}
    if(e.key==='Backspace'){e.preventDefault();convResetView();render();return;}
    if((e.key==='x'||e.key==='ч')&&cvf){
      e.preventDefault();
      if(S.convExcluded[cvf.relPath]){delete S.convExcluded[cvf.relPath];}
      else{S.convExcluded[cvf.relPath]=true;}
      render();return;
    }
    if((e.key==='b'||e.key==='и')&&cvf){
      e.preventDefault();
      S._convBookmarkEdit=!S._convBookmarkEdit;render();return;
    }
    if(e.key===' '&&cvf&&(S.convCropping>0||S.convMaicCrop||S.convInterPanelCrop>0)){
      e.preventDefault();
      _convToggleNoCrop(cvf.relPath);
      render();return;
    }
    if(e.key==='Alt'&&cvf){
      e.preventDefault();
      if(S.convExcluded[cvf.relPath]){delete S.convExcluded[cvf.relPath];}
      else{S.convExcluded[cvf.relPath]=true;}
      render();return;
    }
    return;
  }
  if(S.tab!=='clean')return;
  if(e.key==='Escape'&&(S.artifactCapture||S.artifactDraft||S.showArtifactProfiles)){
    e.preventDefault();S.artifactCapture=null;S.artifactDraft=null;S.showArtifactProfiles=false;S.artifactSaving=false;S.status='';
    render();setTimeout(loadCurrentImage,30);return;
  }
  // Confirm/cancel mask edit
  if(e.key==='Enter'&&_maskEditing){e.preventDefault();confirmMaskEdit();return;}
  if(e.key==='Escape'&&_maskEditing){e.preventDefault();cancelMaskEdit();return;}
  if(e.key==='Escape'&&S.cleanViewOpen){e.preventDefault();saveMask();S.cleanViewOpen=false;resetView();render();return;}
  // Undo/Redo
  if((e.ctrlKey||e.metaKey)&&e.key==='z'&&_maskEditing){e.preventDefault();maskUndo();return;}
  if((e.ctrlKey||e.metaKey)&&(e.key==='y'||e.key==='Z')&&_maskEditing){e.preventDefault();maskRedo();return;}
  // Tools
  if(e.key==='b'||e.key==='и'){S.tool='brush';render();setTimeout(loadCurrentImage,30);}
  if(e.key==='e'||e.key==='у'){S.tool='eraser';render();setTimeout(loadCurrentImage,30);}
  if(e.key==='r'||e.key==='к'){S.tool='rect';render();setTimeout(loadCurrentImage,30);}
  if(e.key==='ArrowLeft'||e.key==='a'||e.key==='ф'){S._navByKey=true;navImage(-1);}if(e.key==='ArrowRight'||e.key==='d'||e.key==='в'){S._navByKey=true;navImage(1);}
  if(e.key==='m'||e.key==='ь'){S.showMask=!S.showMask;drawOverlay();}
});
