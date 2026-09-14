from pathlib import Path
import json
import shutil

content = Path("LandlineMac/ContentView.swift")
text = content.read_text()
old = '''    private func defaultAvatarImage() -> NSImage? {\n        guard let url = Bundle.main.url(forResource: "avatar_toyface", withExtension: "png") else {\n            return nil\n        }\n        return NSImage(contentsOf: url)\n    }\n'''
new = '''    private func defaultAvatarImage() -> NSImage? {\n        NSImage(named: NSImage.Name("ToyBuddha"))\n    }\n'''
if text.count(old) != 1:
    raise RuntimeError("Expected the temporary bundle-file avatar loader exactly once")
content.write_text(text.replace(old, new, 1))

source = Path("prototypes/app/assets/avatar-toyface.png")
if not source.is_file():
    raise RuntimeError(f"Canonical toy-face avatar missing: {source}")

imageset = Path("LandlineMac/Assets.xcassets/ToyBuddha.imageset")
imageset.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, imageset / "avatar-toyface.png")
(imageset / "Contents.json").write_text(json.dumps({
    "images": [
        {
            "filename": "avatar-toyface.png",
            "idiom": "universal",
            "scale": "1x"
        },
        {
            "idiom": "universal",
            "scale": "2x"
        }
    ],
    "info": {
        "author": "xcode",
        "version": 1
    }
}, indent=2) + "\n")

# The first-stage repair copied this standalone file, but this Xcode target's
# resources are explicitly enumerated. The asset catalog is the correct home.
standalone = Path("LandlineMac/Resources/avatar_toyface.png")
if standalone.exists():
    standalone.unlink()

print("Installed canonical toy-face image as ToyBuddha asset-catalog image")
