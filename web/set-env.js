const { writeFileSync, mkdirSync } = require('fs');
const { resolve, dirname } = require('path');

require('dotenv').config({ path: resolve(__dirname, '../.env') });

const targetPath = resolve(__dirname, './env.ts');

mkdirSync(dirname(targetPath), { recursive: true });

const envConfigFile = `
export const environment = {
  production: false,
  apiPort: "${process.env.SCRAPER_PORT}",
};
`;

writeFileSync(targetPath, envConfigFile, { encoding: 'utf-8' });
console.log(`Fichier d'environnement généré : ${targetPath}`);
