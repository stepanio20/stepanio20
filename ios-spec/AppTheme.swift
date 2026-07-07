import SwiftUI

// MARK: - Theme (fixes the black-on-black contrast bug)
// Rule: default text is WHITE (.ink), secondary is light grey (.ink2) — never black.
// Apply `.screen()` to every top-level view so background + default ink are correct.

extension Color {
    static let bg     = Color.black                                  // full-screen background
    static let ink    = Color.white                                 // primary text
    static let ink2   = Color(white: 0.72)                          // secondary text (NOT black)
    static let ink3   = Color(white: 0.55)                          // muted / captions
    static let card   = Color(white: 0.10)                          // cards / rows
    static let card2  = Color(white: 0.14)
    static let stroke = Color(white: 1.0, opacity: 0.10)           // hairline borders
    static let accent = Color(red: 0.45, green: 0.55, blue: 1.0)
    static let good   = Color(red: 0.36, green: 0.83, blue: 0.62)
    static let warn   = Color(red: 1.0,  green: 0.82, blue: 0.40)
}

/// Wrap every screen in this so the background is black and text defaults to white.
struct Screen: ViewModifier {
    func body(content: Content) -> some View {
        content
            .foregroundStyle(Color.ink)          // <- default text color, kills black-on-black
            .tint(.accent)
            .background(Color.bg.ignoresSafeArea())
            .preferredColorScheme(.dark)
    }
}
extension View { func screen() -> some View { modifier(Screen()) } }

// Apply once at the app root:
//
// @main struct IndagaApp: App {
//     @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
//     var body: some Scene { WindowGroup { RootView().screen() } }
// }
