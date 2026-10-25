import {copyFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
await mkdir(new URL('dist/fonts/',root),{recursive:true});
for(const name of ['dm-sans','space-grotesk']){
  const source=new URL(`node_modules/@fontsource-variable/${name}/`,root);
  await copyFile(new URL(`files/${name}-latin-wght-normal.woff2`,source),new URL(`dist/fonts/${name}-latin-variable.woff2`,root));
  await copyFile(new URL('LICENSE',source),new URL(`dist/fonts/${name}-LICENSE.txt`,root));
}
console.log('Local variable fonts copied to '+fileURLToPath(new URL('dist/fonts/',root)));
