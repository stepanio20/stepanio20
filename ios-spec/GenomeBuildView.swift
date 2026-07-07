import SwiftUI

// MARK: - DNA processing screen with real % progress, ETA, and auto-redirect.
//
// Backend contract (GET /genome/job/{id}/status):
//   { "state":"queued|building|ready|failed",
//     "phase":"Matching variants against ClinVar",
//     "percent": 63.5, "eta_seconds": 2600, "report_url": null }
//
// `percent` is PHASE-WEIGHTED on the backend. Reference weights (must sum to 100):
//   1 validate 3 · 2 build index 12 · 3 ClinVar annotate 55 · 4 PGS 15 · 5 traits 10 · 6 assemble 5
// The long one is ClinVar annotation — its own progress = variants_done / variants_total.

struct GenomeJobStatus: Codable {
    enum State: String, Codable { case queued, building, ready, failed }
    let state: State
    let phase: String
    let percent: Double
    let etaSeconds: Int?
    let reportURL: String?
    enum CodingKeys: String, CodingKey {
        case state, phase, percent
        case etaSeconds = "eta_seconds"
        case reportURL = "report_url"
    }
}

@MainActor
final class GenomeBuildVM: ObservableObject {
    @Published var pct: Double = 0
    @Published var phase = "Starting…"
    @Published var etaSeconds: Int?
    @Published var ready = false
    @Published var failed = false
    var reportURL: String?

    private let jobId: String
    private let startedAt = Date()
    private var timer: Timer?
    private let expected: TimeInterval = 2 * 60 * 60          // ~2h average

    // TODO: point at your API
    private var statusURL: URL { URL(string: "https://api.indaga.ai/genome/job/\(jobId)/status")! }

    init(jobId: String) { self.jobId = jobId; start() }
    deinit { timer?.invalidate() }

    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: 12, repeats: true) { [weak self] _ in
            Task { await self?.tick() }
        }
        Task { await tick() }
    }

    private func tick() async {
        guard let (data, _) = try? await URLSession.shared.data(from: statusURL),
              let s = try? JSONDecoder().decode(GenomeJobStatus.self, from: data)
        else { applyTimeFallback(); return }         // no backend % yet → smooth estimate

        withAnimation(.easeInOut(duration: 0.6)) { pct = min(s.percent, s.state == .ready ? 100 : 99) }
        phase = s.phase
        etaSeconds = s.etaSeconds
        if s.state == .failed { failed = true; timer?.invalidate() }
        if s.state == .ready {
            reportURL = s.reportURL
            withAnimation { pct = 100; ready = true }   // triggers redirect
            timer?.invalidate()
        }
    }

    /// Fallback until the backend reports phases: ease toward 95%, never hit 100% early.
    private func applyTimeFallback() {
        let elapsed = Date().timeIntervalSince(startedAt)
        let est = min(95, (elapsed / expected) * 100)
        if est > pct { withAnimation(.easeInOut) { pct = est } }
        etaSeconds = max(0, Int(expected - elapsed))
    }
}

struct GenomeBuildView: View {
    @StateObject var vm: GenomeBuildVM
    var onRedirect: (String) -> Void          // TODO: route to report (deep link / nav)
    var onRestartOnboarding: () -> Void       // TODO: route to onboarding

    var body: some View {
        VStack(spacing: 22) {
            Spacer()
            CircularProgress(pct: vm.pct)
            Text(vm.phase)
                .font(.headline).foregroundStyle(Color.ink)
                .multilineTextAlignment(.center)
            if let eta = vm.etaSeconds, !vm.ready {
                Text("~\(eta / 60) min left").font(.subheadline).foregroundStyle(Color.ink2)
            }
            Text("This usually takes ~2 hours. You can close the app — we'll send a notification when your DNA is ready.")
                .font(.footnote).foregroundStyle(Color.ink3)
                .multilineTextAlignment(.center).padding(.horizontal, 28)

            if vm.failed {
                Text("Something went wrong. Please re-upload your file.")
                    .font(.footnote).foregroundStyle(Color.warn)
            }
            Spacer()
            Button(action: onRestartOnboarding) {
                Text("Start onboarding again")
                    .font(.callout.weight(.semibold))
                    .frame(maxWidth: .infinity).padding(.vertical, 14)
                    .background(Color.card, in: RoundedRectangle(cornerRadius: 14))
                    .foregroundStyle(Color.ink)
            }
            .padding(.horizontal, 20).padding(.bottom, 8)
        }
        .screen()
        .onChange(of: vm.ready) { _, ready in
            if ready { onRedirect(vm.reportURL ?? "indaga://report/genome") }   // auto-redirect
        }
    }
}

struct CircularProgress: View {
    let pct: Double
    var body: some View {
        ZStack {
            Circle().stroke(Color.card2, lineWidth: 12)
            Circle()
                .trim(from: 0, to: pct / 100)
                .stroke(
                    AngularGradient(colors: [.accent, .good], center: .center),
                    style: StrokeStyle(lineWidth: 12, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut, value: pct)
            Text("\(Int(pct))%")
                .font(.system(size: 40, weight: .bold, design: .rounded))
                .foregroundStyle(Color.ink)
        }
        .frame(width: 168, height: 168)
    }
}
