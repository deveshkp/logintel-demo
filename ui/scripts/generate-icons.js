const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const sizes = [16, 32, 64, 192, 512];
const inputSvg = path.join(__dirname, 'public', 'logo.svg');
const outputDir = path.join(__dirname, 'public');

async function generateIcons() {
  try {
    // Read the SVG file
    const svgBuffer = fs.readFileSync(inputSvg);

    // Generate PNGs of different sizes
    for (const size of sizes) {
      await sharp(svgBuffer)
        .resize(size, size)
        .png()
        .toFile(path.join(outputDir, `logo${size}.png`));
      
      console.log(`Generated ${size}x${size} PNG`);
    }

    // Generate favicon.ico (combines 16x16, 32x32, and 64x64)
    const favicon = await sharp(svgBuffer)
      .resize(64, 64)
      .toFormat('ico')
      .toFile(path.join(outputDir, 'favicon.ico'));

    console.log('Generated favicon.ico');
    
  } catch (error) {
    console.error('Error generating icons:', error);
  }
}

generateIcons();