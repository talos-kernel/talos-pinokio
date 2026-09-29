const release = require('./release.json');
module.exports = {
  version: '8.2',
  title: 'Talos',
  description: 'Self-hosted AI assistant. Use your own models, approve one action or a whole task, and inspect what ran. Alpha release.',
  icon: 'icon.png',
  menu: async (kernel, info) => {
    if (!['darwin','linux'].includes(process.platform)) {
      return [{text:'macOS and Linux only',href:'https://talos-agent.ch/docs/'}];
    }
    for (const [file,label] of [['install.js','Installing'],['setup.js','Set up'],['start.js','Chat'],['doctor.js','Diagnostics'],['status.js','Status'],['verify.js','Verify event log']]) {
      if(info.running(file))return [{text:label,href:file,default:true}];
    }
    if(!info.exists('app/.pinokio-installed.json')) {
      return [{text:`Install Talos ${release.version}`,href:'install.js',default:true},
              {text:'Read the guide',href:'README.md'}];
    }
    return [{text:'Set up',href:'setup.js'}, {text:'Open chat',href:'start.js'},
            {text:'Diagnostics',href:'doctor.js'}, {text:'Status',href:'status.js'},
            {text:'Verify event log',href:'verify.js'},
            {text:'Read the guide',href:'README.md'}];
  }
};
