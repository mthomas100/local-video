// faces.swift — every face in every frame of a video, with its lips, from macOS Vision (2026-09-27, iteration 5).
// Why: MediaPipe's face detector found no face in liminal-clowns shot 2 (a medium shot) and in only 13% of shot 7 (a
// frontal close-up of a clown in cracked-porcelain paint). Vision found faces in both. CPU only (beside a render).
// Prints one JSON line per frame: {"i": n, "faces": [{"box": [x0,y0,x1,y1], "inner": [[x,y]...], "outer": [[x,y]...],
// "q": quality}]}, pixels, origin top left. Usage: faces <video.mp4>
import Foundation
import Vision
import AVFoundation

guard CommandLine.arguments.count == 2 else { fputs("usage: faces <video>\n", stderr); exit(2) }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let asset = AVURLAsset(url: url)
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack?
Task { track = try? await asset.loadTracks(withMediaType: .video).first; sem.signal() }
sem.wait()
guard let vt = track, let reader = try? AVAssetReader(asset: asset) else { fputs("cannot read \(url.path)\n", stderr); exit(1) }
let out = AVAssetReaderTrackOutput(track: vt, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

func cpuOnly(_ r: VNRequest) {
    if #available(macOS 14.0, *) {
        if let cpu = (try? r.supportedComputeStageDevices)?[.main]?.first(where: { if case .cpu = $0 { return true } else { return false } }) {
            r.setComputeDevice(cpu, for: .main)
        }
    } else { r.usesCPUOnly = true }
}
func pts(_ region: VNFaceLandmarkRegion2D?, _ w: Int, _ h: Int) -> [[Double]] {
    guard let r = region else { return [] }
    return r.pointsInImage(imageSize: CGSize(width: w, height: h)).map { [Double($0.x), Double(h) - Double($0.y)] }
}
var i = 0
while let sb = out.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let w = CVPixelBufferGetWidth(pb), h = CVPixelBufferGetHeight(pb)
    let req = VNDetectFaceLandmarksRequest()
    cpuOnly(req)
    let q = VNDetectFaceCaptureQualityRequest()
    cpuOnly(q)
    let handler = VNImageRequestHandler(cvPixelBuffer: pb, options: [:])
    var faces: [[String: Any]] = []
    if (try? handler.perform([req])) != nil {
        for f in req.results ?? [] {
            let b = f.boundingBox
            faces.append(["box": [Double(b.minX) * Double(w), (1 - Double(b.maxY)) * Double(h), Double(b.maxX) * Double(w), (1 - Double(b.minY)) * Double(h)],
                          "inner": pts(f.landmarks?.innerLips, w, h), "outer": pts(f.landmarks?.outerLips, w, h),
                          "roll": f.roll?.doubleValue ?? 0, "yaw": f.yaw?.doubleValue ?? 0])
        }
    }
    let line: [String: Any] = ["i": i, "w": w, "h": h, "faces": faces]
    if let d = try? JSONSerialization.data(withJSONObject: line), let s = String(data: d, encoding: .utf8) { print(s) }
    i += 1
}
