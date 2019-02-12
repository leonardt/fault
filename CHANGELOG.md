# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.4]
### Added
- Adds support for arrays and tuples in setattr interface.

## [1.0.3]
### Fixed
- Fixed bug in .sv file logic for VerilogTarget

## [1.0.2]
### Added
- Added support for .sv files to VerilogTarget

## [1.0.1]
### Fixed
- Fixed functional tester's use of self.circuit which was not updated for the
  new Tester setattr interface

## 1.0.0
### Added
- Added preliminary support for peek and expect on internal signals and poke on
  internal registers

[Unreleased]: https://github.com/leonardt/fault/compare/v1.0.3...HEAD
[1.0.4]: https://github.com/leonardt/fault/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/leonardt/fault/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/leonardt/fault/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/leonardt/fault/compare/v1.0.0...v1.0.1
