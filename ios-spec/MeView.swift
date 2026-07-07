import SwiftUI

// MARK: - "Me" tab. Version at the very bottom; turns GREEN with
// "Please update your app" when a newer App Store version exists.

struct MeView: View {
    @StateObject private var updates = AppUpdateChecker()

    var body: some View {
        List {
            // ... your existing Me rows (profile, connections, settings) ...

            Section {
                EmptyView()
            } footer: {
                VStack(spacing: 6) {
                    Text("Indaga")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(Color.ink2)

                    if updates.updateAvailable {
                        // green highlight + call to action
                        Link(destination: updates.storeURL) {
                            HStack(spacing: 6) {
                                Image(systemName: "arrow.down.circle.fill")
                                Text("Please update your app")
                                    .font(.caption.weight(.semibold))
                            }
                            .foregroundStyle(Color.good)
                        }
                        Text("v\(Bundle.appVersion) → \(updates.latestVersion ?? "new") available")
                            .font(.caption2)
                            .foregroundStyle(Color.good)
                    } else {
                        Text("v\(Bundle.appVersion) (\(Bundle.buildNumber))")
                            .font(.caption2)
                            .foregroundStyle(Color.ink3)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 28)
                .padding(.bottom, 8)
            }
            .listRowBackground(Color.clear)
        }
        .scrollContentBackground(.hidden)
        .screen()
        .navigationTitle("Me")
        .task { await updates.check() }
    }
}

extension Bundle {
    static var appVersion: String { main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0" }
    static var buildNumber: String { main.infoDictionary?["CFBundleVersion"] as? String ?? "1" }
}
