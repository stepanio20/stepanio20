import SwiftUI
import WebKit

// MARK: - Onboarding funnel (the 5 A/B variants) embedded in the app.
//
// The funnels are static web pages (built in `funnels/`). Once GitHub Pages is on,
// they live at:  https://stepanio20.github.io/stepanio20/1 … /5
// Random-assign a variant per new user for A/B testing; persist the choice.

struct OnboardingFlow: View {
    @AppStorage("onboarding_variant") private var variant: Int = 0
    var onFinished: () -> Void

    var body: some View {
        // assign a variant once (1...5), then always show the same one to this user
        let v = variant == 0 ? Int.random(in: 1...5) : variant
        OnboardingWebView(variant: v, onFinished: onFinished)
            .ignoresSafeArea()
            .screen()
            .onAppear { if variant == 0 { variant = v } }
    }
}

struct OnboardingWebView: UIViewRepresentable {
    let variant: Int
    var onFinished: () -> Void

    // TODO: replace with your deployed funnel base URL (GitHub Pages / Vercel / custom domain)
    private var baseURL: String { "https://stepanio20.github.io/stepanio20" }

    func makeCoordinator() -> Coordinator { Coordinator(onFinished: onFinished) }

    func makeUIView(context: Context) -> WKWebView {
        let cfg = WKWebViewConfiguration()
        // bridge so the funnel can tell the app "done" via window.webkit.messageHandlers.app.postMessage(...)
        cfg.userContentController.add(context.coordinator, name: "app")
        let web = WKWebView(frame: .zero, configuration: cfg)
        web.isOpaque = false
        web.backgroundColor = .black          // avoid white flash on load
        web.scrollView.backgroundColor = .black
        return web
    }

    func updateUIView(_ web: WKWebView, context: Context) {
        if let url = URL(string: "\(baseURL)/\(variant)") {
            web.load(URLRequest(url: url))
        }
    }

    final class Coordinator: NSObject, WKScriptMessageHandler {
        let onFinished: () -> Void
        init(onFinished: @escaping () -> Void) { self.onFinished = onFinished }
        // funnel calls: window.webkit.messageHandlers.app.postMessage({event:"onboarding_done"})
        func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
            if let body = m.body as? [String: Any], body["event"] as? String == "onboarding_done" {
                onFinished()
            }
        }
    }
}

// "Start onboarding again" — call this from the DNA build screen button or Me tab:
//   router.presentOnboarding()  → shows OnboardingFlow { router.dismissOnboarding() }
