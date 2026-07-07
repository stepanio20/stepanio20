import UIKit
import UserNotifications

// MARK: - "Your DNA data is ready" push (APNs) + deep-link routing.
//
// Flow: backend finishes the ~2h job → sends an APNs push with
//   aps.alert = "Your DNA data is ready 🧬"
//   data.deep_link = "indaga://report/genome"
// Tapping it routes to the report. (Local notifications can't do this — the app
// isn't running during a 2h server job — so the trigger MUST be a server push.)

final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        requestPushPermission()
        return true
    }

    func requestPushPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async { UIApplication.shared.registerForRemoteNotifications() }
        }
    }

    // Device token → send to backend so it can push this device when the job is done.
    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        // TODO: POST token to your backend, associated with the user + genome job id.
        Task { try? await Backend.registerPushToken(token) }
    }

    // Tap on the notification → route to the deep link.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse) async {
        let info = response.notification.request.content.userInfo
        if let link = info["deep_link"] as? String, let url = URL(string: link) {
            await MainActor.run { RootRouter.shared.open(url) }   // e.g. indaga://report/genome
        }
    }

    // Show the banner even if the app is foregrounded.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .sound]
    }
}

// Minimal router stub — replace with your real navigation.
final class RootRouter: ObservableObject {
    static let shared = RootRouter()
    @Published var pendingURL: URL?
    func open(_ url: URL) { pendingURL = url }   // your RootView observes this and navigates
}

enum Backend {
    static func registerPushToken(_ token: String) async throws {
        // TODO: implement against your API
    }
}
