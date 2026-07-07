import SwiftUI

// MARK: - Green "Please update your app" banner, shown at the top of the app.
// Only appears when a newer version is on the App Store. Tap → App Store.
//
// Usage — put at the top of your root content:
//   VStack(spacing: 0) {
//       AppUpdateBanner(checker: updates)
//       TabView { ... }
//   }
//   .task { await updates.check() }

struct AppUpdateBanner: View {
    @ObservedObject var checker: AppUpdateChecker

    // dark ink on the light-green highlight = readable (banner is intentionally green)
    private let onGreen = Color(red: 0.03, green: 0.20, blue: 0.10)

    var body: some View {
        if checker.updateAvailable {
            Link(destination: checker.storeURL) {
                HStack(spacing: 10) {
                    Image(systemName: "arrow.down.circle.fill").font(.title3)
                    VStack(alignment: .leading, spacing: 1) {
                        Text("Please update your app").font(.subheadline.weight(.bold))
                        if let v = checker.latestVersion {
                            Text("Version \(v) is available").font(.caption)
                        }
                    }
                    Spacer()
                    Text("UPDATE")
                        .font(.caption2.weight(.heavy))
                        .padding(.horizontal, 12).padding(.vertical, 6)
                        .background(onGreen.opacity(0.14), in: Capsule())
                }
                .foregroundStyle(onGreen)
                .padding(.horizontal, 14).padding(.vertical, 11)
                .background(Color.good)                       // the green highlight
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .padding(.horizontal, 12).padding(.top, 6)
            }
            .transition(.move(edge: .top).combined(with: .opacity))
            .animation(.easeInOut, value: checker.updateAvailable)
        }
    }
}
