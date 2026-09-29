const test = require('node:test');
const assert = require('node:assert/strict');
const menu = require('../pinokio.js');

test('fresh install has only install and documentation', async () => {
  const items = await menu.menu({}, {running:()=>false,exists:()=>false});
  assert.deepEqual(items.map(x=>x.href), ['install.js','README.md']);
});
test('installed app exposes real CLI actions without reset or silent upgrade', async () => {
  const items = await menu.menu({}, {running:()=>false,exists:()=>true});
  assert.deepEqual(items.map(x=>x.href), ['setup.js','start.js','doctor.js','status.js','verify.js','README.md']);
  assert.ok(items.every(item=>!item.default), 'opening the app must not silently start a model session');
});
test('running process stays visible', async () => {
  for (const file of ['install.js','setup.js','start.js','doctor.js','status.js','verify.js']) {
    const items = await menu.menu({}, {running:name=>name===file,exists:()=>true});
    assert.equal(items.length,1);
    assert.equal(items[0].href,file);
  }
});
test('only setup and chat are interactive, no sharing or daemon', () => {
  for (const [file,action,interactive] of [['install','install',false],['setup','setup',true],['start','chat',true],['doctor','doctor',false],['status','status',false],['verify','verify',false]]) {
    const script = require(`../${file}.js`);
    assert.equal(script.run.length,1);
    assert.equal(script.run[0].method,'shell.run');
    assert.equal(script.run[0].params.message,`python launcher.py ${action}`);
    assert.equal(script.run[0].params.interactive,interactive);
    assert.equal(script.run[0].params.input,interactive);
    if (interactive) {
      let stopped = false;
      script.run[0].params.onprompt({kill:()=>{stopped=true;}});
      assert.equal(stopped,true,'returning to the shell must release the launcher menu');
    }
    assert.equal(script.daemon,undefined);
  }
});
