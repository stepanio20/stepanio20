import SwiftUI

// MARK: - "Me" tab with the version label at the very bottom.

struct MeView: View {
    var body: some View {
        List {
            // ... your existing Me rows go here (profile, connections, settings) ...

            Section {
                EmptyView()
            } footer: {
                VStack(spacing: 4) {
                    Text("Indaga")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(Color.ink2)
                    Text("v\(Bundle.appVersion) (\(Bundle.buildNumber))")
                        .font(.caption2)
                        .foregroundStyle(Color.ink3)
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 28)
                .padding(.bottom, 8)
            }
            .listRowBackground(Color.clear)
        }
        .scrollContentBackground(.hidden)   // let the black background show through
        .screen()
        .navigationTitle("Me")
    }
}

extension Bundle {
    static var appVersion: String { main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0" }
    static var buildNumber: String { main.infoDictionary?["CFBundleVersion"] as? String ?? "1" }
}
