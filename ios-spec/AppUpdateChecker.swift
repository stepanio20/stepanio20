import Foundation

// MARK: - "Update available" detection.
// Compares the installed version to the latest App Store version (iTunes Lookup API).
// When newer → drives the green banner + green version row.

@MainActor
final class AppUpdateChecker: ObservableObject {
    @Published var updateAvailable = false
    @Published var latestVersion: String?

    // TODO: your numeric App Store app id (from App Store Connect) — for the "Update" link.
    private let appStoreId = "000000000"
    private let bundleId = Bundle.main.bundleIdentifier ?? ""

    var storeURL: URL { URL(string: "https://apps.apple.com/app/id\(appStoreId)")! }

    /// Call from `.task { await checker.check() }` on the root / Me screen.
    func check() async {
        guard let url = URL(string: "https://itunes.apple.com/lookup?bundleId=\(bundleId)"),
              let (data, _) = try? await URLSession.shared.data(from: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["results"] as? [[String: Any]],
              let store = results.first?["version"] as? String
        else { return }

        latestVersion = store
        updateAvailable = isNewer(store, than: Bundle.appVersion)   // e.g. "1.3.0" > "1.2.0"
    }

    private func isNewer(_ a: String, than b: String) -> Bool {
        a.compare(b, options: .numeric) == .orderedDescending
    }
}
