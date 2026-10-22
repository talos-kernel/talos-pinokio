const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const menu = require('../pinokio.js');
const release = require('../release.json');

test('release pin is exactly Talos beta.5 and public wording is beta', () => {
  assert.deepEqual(release, {
    version: '0.20.0-beta.5',
    source_commit: 'b05e8ecc4c0669e870eb4b4371cf6f53d59bd2d7',
    installer_url: 'https://raw.githubusercontent.com/talos-kernel/Talos/b05e8ecc4c0669e870eb4b4371cf6f53d59bd2d7/site/install.sh',
    installer_sha256: 'f1e676f8aff53ddb7e5e1a698a53c085cc40bbbc1d7c4df9271e1f483e20e752',
  });
  for (const file of ['README.md', 'pinokio.js', 'pinokio.json']) {
    const contents = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    assert.match(contents, /\bbeta\b/i, `${file} must describe the beta release`);
    assert.doesNotMatch(contents, /\balpha\b/i, `${file} must not retain alpha wording`);
  }
  const readme = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');
  assert.ok(readme.includes(release.version), 'README must name the pinned release');
  assert.doesNotMatch(readme, /0\.20\.0-beta\.4/, 'README must not advertise the old pin');
  assert.match(readme, /Apple Silicon/, 'macOS architecture requirement must be explicit');
});

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
