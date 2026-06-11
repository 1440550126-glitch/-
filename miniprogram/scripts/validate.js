const fs = require('fs');
const path = require('path');
function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(dir, entry.name);
    if (file.includes(`${path.sep}.git${path.sep}`) || file.includes('node_modules')) return [];
    return entry.isDirectory() ? walk(file) : [file];
  });
}
let ok = true;
for (const file of walk(process.cwd()).filter((item) => /\.(js|json)$/.test(item))) {
  try {
    const source = fs.readFileSync(file, 'utf8');
    if (file.endsWith('.json')) JSON.parse(source);
    else new Function(source);
  } catch (error) {
    ok = false;
    console.error(`Invalid ${path.relative(process.cwd(), file)}: ${error.message}`);
  }
}
if (!ok) process.exit(1);
console.log('All JavaScript and JSON files are syntactically valid.');
