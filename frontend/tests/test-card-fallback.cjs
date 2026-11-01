const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const Module=require('node:module');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {transform}=require('next/dist/build/swc');
(async()=>{
  const filename=path.resolve(__dirname,'../components/GeneratedBusinessCard.jsx');
  const {code}=await transform(fs.readFileSync(filename,'utf8'),{filename,jsc:{parser:{syntax:'ecmascript',jsx:true},transform:{react:{runtime:'classic'}}},module:{type:'commonjs'}});
  const old=require.extensions['.css'];require.extensions['.css']=(m)=>{m.exports={};};
  try{
    const mod=new Module(filename,module);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));mod._compile(code,filename);
    let calls=0;const html=renderToStaticMarkup(React.createElement(mod.exports.default,{card:{card_id:'unknown',card_type:'unknown-tool',title:'Untrusted card',permission_level:'RED',data:{action:'transfer.execute'}},onAction:()=>calls++}));
    assert.match(html,/已安全降级为只读提示/);assert.doesNotMatch(html,/<button/);assert.equal(calls,0);
    assert.equal(renderToStaticMarkup(React.createElement(mod.exports.default,{card:null})), '');
    console.log('PASS: unknown card_type renders read-only fallback, no action buttons/callbacks; null card safe.');
  }finally{if(old)require.extensions['.css']=old;else delete require.extensions['.css'];}
})().catch(e=>{console.error(e);process.exit(1)});
