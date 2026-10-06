// facescore.swift — score image files by face quality with macOS Vision (2026-09-22).
// Prints one line per image: "<score>\t<faces>\t<path>". Score = sum over the largest
// `want` faces of (Vision capture quality 0..1) x (face area fraction), so a big, sharp,
// frontal face wins; images with fewer than `want` faces score 0. Usage:
//   swift facescore.swift <want-faces> <image>...
import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 3, let want = Int(args[1]) else { fputs("usage: facescore <want-faces> <image>...\n", stderr); exit(2) }
for path in args.dropFirst(2) {
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("0\t0\t\(path)"); continue
    }
    let req = VNDetectFaceCaptureQualityRequest()
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch { print("0\t0\t\(path)"); continue }
    let faces = (req.results ?? []).map { f -> (Double, Double) in
        let area = Double(f.boundingBox.width * f.boundingBox.height)
        return (Double(f.faceCaptureQuality ?? 0), area)
    }.sorted { $0.1 > $1.1 }
    var score = 0.0
    if faces.count >= want { for f in faces.prefix(want) { score += f.0 * f.1 } }
    print(String(format: "%.5f\t%d\t%@", score, faces.count, path))
}
