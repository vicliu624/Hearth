import fs from 'node:fs';
import path from 'node:path';

const lock=JSON.parse(fs.readFileSync('package-lock.json','utf8'));
const notices=['Hearth frontend: third-party notices\n'];
for(const [entry,metadata] of Object.entries(lock.packages)) {
  if(!entry || metadata.dev)continue;
  const candidates=['LICENSE','LICENSE.md','LICENSE.txt','license','license.md','License.md'];
  const file=candidates.map(name=>path.join(entry,name)).find(candidate=>fs.existsSync(candidate));
  notices.push(`\n${entry.replace(/^node_modules\//,'')} ${metadata.version}\n${'='.repeat(60)}\n`);
  notices.push(file?fs.readFileSync(file,'utf8'):`License: ${metadata.license || 'See package metadata'}`);
}
fs.mkdirSync('public/legal',{recursive:true});
fs.writeFileSync('public/legal/THIRD_PARTY_NOTICES.txt',notices.join('\n'));
