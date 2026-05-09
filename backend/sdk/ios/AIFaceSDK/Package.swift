// swift-tools-version:5.5

import PackageDescription

let package = Package(
    name: "AIFaceSDK",
    platforms: [
        .iOS(.v14),
        .macOS(.v11)
    ],
    products: [
        .library(
            name: "AIFaceSDK",
            targets: ["AIFaceSDK"]
        ),
    ],
    targets: [
        .target(
            name: "AIFaceSDK",
            dependencies: [],
            path: "Sources/AIFaceSDK"
        ),
        .testTarget(
            name: "AIFaceSDKTests",
            dependencies: ["AIFaceSDK"],
            path: "Tests"
        ),
    ]
)
