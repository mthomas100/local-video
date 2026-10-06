// facebox.swift — face boxes in image files with macOS Vision, for identity boards (2026-09-26).
// Prints one JSON object per image: {"path": ..., "w": W, "h": H, "faces": [{"x","y","w","h","q"}]}.
// Boxes are in pixels with the origin at the top left (Vision's are normalised, bottom left), largest
// face first; q is Vision's face capture quality (0..1, higher = sharper and more frontal).
// Runs on the CPU only, so it can run beside a render or a loaded model. Usage:
//   swift facebox.swift <image>...
import Foundation
import Vision
import AppKit

let paths = CommandLine.arguments.dropFirst()
guard !paths.isEmpty else { fputs("usage: facebox <image>...\n", stderr); exit(2) }
for path in paths {
    var faces: [[String: Double]] = []
    var w = 0, h = 0
    if let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        w = cg.width; h = cg.height
        let req = VNDetectFaceCaptureQualityRequest()
        if #available(macOS 14.0, *) {
            if let cpu = (try? req.supportedComputeStageDevices)?[.main]?.first(where: { if case .cpu = $0 { return true } else { return false } }) {
                req.setComputeDevice(cpu, for: .main)
            }
        } else {
            req.usesCPUOnly = true
        }
        let handler = VNImageRequestHandler(cgImage: cg, options: [:])
        if (try? handler.perform([req])) != nil {
            for f in req.results ?? [] {
                let b = f.boundingBox
                faces.append(["x": Double(b.minX) * Double(w), "y": (1 - Double(b.maxY)) * Double(h),
                              "w": Double(b.width) * Double(w), "h": Double(b.height) * Double(h),
                              "q": Double(f.faceCaptureQuality ?? 0)])
            }
        }
    }
    faces.sort { ($0["w"]! * $0["h"]!) > ($1["w"]! * $1["h"]!) }
    let obj: [String: Any] = ["path": path, "w": w, "h": h, "faces": faces]
    if let data = try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys]), let s = String(data: data, encoding: .utf8) {
        print(s)
    }
}
