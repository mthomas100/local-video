// mouth.swift — mouth opening per image with macOS Vision face landmarks, for the lip-sync meter (2026-09-27).
// Prints one JSON line per image: {"i": index, "open": inner-lip height / face height, or null when no face}.
// The largest face is used. CPU only (Vision on the CPU), so it runs beside a render or a loaded model.
//   swift mouth.swift frame-0001.png frame-0002.png ...
import Foundation
import Vision
import AppKit

func innerOpen(_ f: VNFaceObservation) -> Double? {
    guard let lm = f.landmarks, let lips = lm.innerLips ?? lm.outerLips else { return nil }
    let ys = lips.normalizedPoints.map { Double($0.y) }
    guard let mx = ys.max(), let mn = ys.min() else { return nil }
    return mx - mn   // normalised to the face box height already (landmark points are face-relative)
}
for (i, path) in CommandLine.arguments.dropFirst().enumerated() {
    var val: Double? = nil
    var area = 0.0
    if let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        let req = VNDetectFaceLandmarksRequest()
        if #available(macOS 14.0, *) {
            if let cpu = (try? req.supportedComputeStageDevices)?[.main]?.first(where: { if case .cpu = $0 { return true } else { return false } }) {
                req.setComputeDevice(cpu, for: .main)
            }
        }
        let h = VNImageRequestHandler(cgImage: cg, options: [:])
        if (try? h.perform([req])) != nil, let faces = req.results, !faces.isEmpty {
            let f = faces.max { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height }!
            val = innerOpen(f)
            area = Double(f.boundingBox.width * f.boundingBox.height)
        }
    }
    let o: [String: Any] = ["i": i, "open": val.map { $0 as Any } ?? NSNull(), "area": area]
    if let d = try? JSONSerialization.data(withJSONObject: o), let s = String(data: d, encoding: .utf8) { print(s) }
}
