#!/usr/bin/env python3
"""
Memfault Firmware SDK SBOM Generator

This script scans the Memfault firmware SDK and generates a Software Bill of Materials (SBOM)
in SPDX format. It identifies components, dependencies, licenses, and creates relationships
between the different parts of the SDK.

Usage:
    python generate_sbom.py [--output-file sbom.spdx] [--format json|tag|yaml]
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml


class LicenseDetector:
    """Detects licenses in source files and provides SPDX license identifiers."""

    def __init__(self):
        self.LICENSE_PATTERNS = {
            "Memfault": r"(?i)copyright.*memfault|memfault.*license",
            "MIT": r"(?i)mit license|permission is hereby granted, free of charge",
            "Apache-2.0": r"(?i)apache license|version 2\.0",
            "BSD-3-Clause": r"(?i)bsd.*3-clause|redistribution and use in source and binary forms",
            "GPL-2.0": r"(?i)gnu general public license.*version 2",
            "GPL-3.0": r"(?i)gnu general public license.*version 3",
            "LGPL-2.1": r"(?i)gnu lesser general public license.*version 2\.1",
            "ISC": r"(?i)isc license|permission to use, copy, modify",
        }

    def detect_license(self, content: str, file_path: str = ""):
        """Detect license from file content."""
        # First check for SPDX identifiers
        spdx_match = re.search(
            r"SPDX-License-Identifier:\s*([^\s\n]+)", content, re.IGNORECASE
        )
        if spdx_match:
            return spdx_match.group(1)

        # Check license patterns
        for license_id, pattern in self.LICENSE_PATTERNS.items():
            if re.search(pattern, content):
                return license_id

        return "NOASSERTION"


class FileAnalyzer:
    """Analyzes individual files for metadata, dependencies, and relationships."""

    def __init__(self, license_detector):
        self.license_detector = license_detector

    def get_file_hash(self, file_path: Path):
        """Calculate SHA1 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha1(f.read()).hexdigest()
        except Exception:
            return ""

    def analyze_c_file(self, file_path: Path):
        """Analyze C/C++ source file for includes and dependencies."""
        includes = set()
        dependencies = set()

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                license_id = self.license_detector.detect_license(
                    content, str(file_path)
                )

                # Extract #include statements
                include_pattern = r'#include\s*[<"](.*?)[>"]'
                for match in re.finditer(include_pattern, content):
                    include_file = match.group(1)
                    includes.add(include_file)

                    # Identify external dependencies
                    if not include_file.startswith("memfault/"):
                        dependencies.add(include_file.split("/")[0])

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            license_id = "NOASSERTION"

        return {
            "includes": list(includes),
            "dependencies": list(dependencies),
            "license": license_id,
            "hash": self.get_file_hash(file_path),
        }


class ComponentAnalyzer:
    """Analyzes SDK components and their relationships."""

    def __init__(self, sdk_root: Path, file_analyzer):
        self.sdk_root = sdk_root
        self.file_analyzer = file_analyzer
        self.components = {}
        self.external_deps = set()

    def analyze_component(self, component_path: Path):
        """Analyze a single SDK component."""
        component_name = component_path.name
        source_files = []
        header_files = []
        dependencies = set()
        licenses = set()

        # Scan for source files
        for pattern in ["**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp"]:
            for file_path in component_path.glob(pattern):
                if file_path.is_file():
                    analysis = self.file_analyzer.analyze_c_file(file_path)

                    file_info = {
                        "path": str(file_path.relative_to(self.sdk_root)),
                        "hash": analysis["hash"],
                        "license": analysis["license"],
                        "includes": analysis["includes"],
                    }

                    if file_path.suffix in [".c", ".cpp"]:
                        source_files.append(file_info)
                    elif file_path.suffix in [".h", ".hpp"]:
                        header_files.append(file_info)

                    dependencies.update(analysis["dependencies"])
                    licenses.add(analysis["license"])

        # Read component README if exists
        readme_path = component_path / "README.md"
        description = f"Memfault SDK {component_name} component"
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read()
                    # Extract first meaningful line as description
                    lines = [
                        line.strip()
                        for line in readme_content.split("\n")
                        if line.strip()
                    ]
                    for line in lines[1:]:  # Skip first line (usually title)
                        if not line.startswith("#") and len(line) > 20:
                            description = line
                            break
            except Exception:
                pass

        self.external_deps.update(dependencies)

        return {
            "name": component_name,
            "description": description,
            "source_files": source_files,
            "header_files": header_files,
            "dependencies": list(dependencies),
            "licenses": list(licenses),
        }

    def analyze_all_components(self, additional_excludes=None):
        """Analyze all SDK components and source files."""
        # First analyze the main components directory
        components_dir = self.sdk_root / "components"

        if components_dir.exists():
            for component_dir in components_dir.iterdir():
                if component_dir.is_dir():
                    self.components[f"components-{component_dir.name}"] = (
                        self.analyze_component(component_dir)
                    )

        # Now recursively analyze all other directories except examples
        exclude_dirs = {
            "examples",
            "tests",
            ".git",
            "__pycache__",
            "build",
            "dist",
            ".vscode",
            ".idea",
        }
        if additional_excludes:
            exclude_dirs.update(additional_excludes)

        self._analyze_directory_recursive(self.sdk_root, exclude_dirs)

    def _analyze_directory_recursive(self, directory: Path, exclude_dirs=None):
        """Recursively analyze directories for source files, excluding specified directories."""
        if exclude_dirs is None:
            exclude_dirs = {
                "examples",
                "tests",
                ".git",
                "__pycache__",
                "build",
                "dist",
                ".vscode",
                ".idea",
            }

        for item in directory.iterdir():
            if item.is_dir() and item.name not in exclude_dirs:
                # Check if this directory has source files
                source_files = []
                header_files = []
                dependencies = set()
                licenses = set()

                # Look for C/C++ files in this directory (non-recursive for this level)
                for pattern in ["*.c", "*.cpp", "*.h", "*.hpp"]:
                    for file_path in item.glob(pattern):
                        if file_path.is_file():
                            analysis = self.file_analyzer.analyze_c_file(file_path)

                            file_info = {
                                "path": str(file_path.relative_to(self.sdk_root)),
                                "hash": analysis["hash"],
                                "license": analysis["license"],
                                "includes": analysis["includes"],
                            }

                            if file_path.suffix in [".c", ".cpp"]:
                                source_files.append(file_info)
                            elif file_path.suffix in [".h", ".hpp"]:
                                header_files.append(file_info)

                            dependencies.update(analysis["dependencies"])
                            licenses.add(analysis["license"])

                # If we found source files, add this as a component
                if source_files or header_files:
                    relative_path = str(item.relative_to(self.sdk_root))
                    component_name = relative_path.replace("/", "-")

                    # Read README if exists for description
                    description = f"Source files in {relative_path}"
                    readme_path = item / "README.md"
                    if readme_path.exists():
                        try:
                            with open(readme_path, "r", encoding="utf-8") as f:
                                readme_content = f.read()
                                # Extract first meaningful line as description
                                lines = [
                                    line.strip()
                                    for line in readme_content.split("\n")
                                    if line.strip()
                                ]
                                for line in lines[
                                    1:
                                ]:  # Skip first line (usually title)
                                    if not line.startswith("#") and len(line) > 20:
                                        description = line
                                        break
                        except Exception:
                            pass

                    self.external_deps.update(dependencies)

                    self.components[component_name] = {
                        "name": component_name,
                        "description": description,
                        "source_files": source_files,
                        "header_files": header_files,
                        "dependencies": list(dependencies),
                        "licenses": list(licenses),
                    }

                # Recursively analyze subdirectories
                self._analyze_directory_recursive(item, exclude_dirs)


class SPDXGenerator:
    """Generates SPDX-format SBOM."""

    def __init__(self, sdk_root: Path, components, external_deps):
        self.sdk_root = sdk_root
        self.components = components
        self.external_deps = external_deps
        self.spdx_id_counter = 1

    def generate_spdx_id(self):
        """Generate unique SPDX ID."""
        spdx_id = f"SPDXRef-{self.spdx_id_counter}"
        self.spdx_id_counter += 1
        return spdx_id

    def get_version_info(self):
        """Extract version information from VERSION file."""
        version_file = self.sdk_root / "VERSION"
        version_info = {
            "version": "unknown",
            "commit": "unknown",
            "build_id": "unknown",
        }

        try:
            with open(version_file, "r") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("VERSION:"):
                        version_info["version"] = line.split(":", 1)[1].strip()
                    elif line.startswith("GIT COMMIT:"):
                        version_info["commit"] = line.split(":", 1)[1].strip()
                    elif line.startswith("BUILD ID:"):
                        version_info["build_id"] = line.split(":", 1)[1].strip()
        except Exception:
            pass

        return version_info

    def generate_json_spdx(self):
        """Generate SPDX document in JSON format."""
        version_info = self.get_version_info()
        creation_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Document metadata
        spdx_doc = {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "creationInfo": {
                "created": creation_time,
                "creators": ["Tool: Memfault SDK SBOM Generator"],
                "licenseListVersion": "3.19",
            },
            "name": "Memfault Firmware SDK",
            "dataLicense": "CC0-1.0",
            "documentNamespace": f"https://memfault.com/sbom/{version_info['version']}-{creation_time}",
            "packages": [],
            "files": [],
            "relationships": [],
        }

        # Keep track of file IDs for relationships
        file_ids = {}

        # Add individual files
        for comp_name, comp_data in self.components.items():
            # Process source files
            for file_info in comp_data.get("source_files", []):
                file_id = self.generate_spdx_id()
                file_path = file_info["path"]
                file_ids[file_path] = file_id

                file_entry = {
                    "SPDXID": file_id,
                    "fileName": f"./{file_path}",
                    "checksums": [
                        {"algorithm": "SHA1", "checksumValue": file_info["hash"]}
                    ],
                    "licenseConcluded": file_info["license"],
                    "copyrightText": "Copyright (c) Memfault, Inc.",
                }
                spdx_doc["files"].append(file_entry)

            # Process header files
            for file_info in comp_data.get("header_files", []):
                file_id = self.generate_spdx_id()
                file_path = file_info["path"]
                file_ids[file_path] = file_id

                file_entry = {
                    "SPDXID": file_id,
                    "fileName": f"./{file_path}",
                    "checksums": [
                        {"algorithm": "SHA1", "checksumValue": file_info["hash"]}
                    ],
                    "licenseConcluded": file_info["license"],
                    "copyrightText": "Copyright (c) Memfault, Inc.",
                }
                spdx_doc["files"].append(file_entry)

        # Main package
        main_package_id = self.generate_spdx_id()
        main_package = {
            "SPDXID": main_package_id,
            "name": "memfault-firmware-sdk",
            "downloadLocation": "https://github.com/memfault/memfault-firmware-sdk",
            "filesAnalyzed": True,
            "versionInfo": version_info["version"],
            "supplier": "Organization: Memfault",
            "homepage": "https://memfault.com",
            "licenseConcluded": "NOASSERTION",  # Custom license
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "Copyright (c) 2019 - Present, Memfault",
            "description": "Memfault SDK for embedded systems. Observability, logging, crash reporting, and OTA all in one service.",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "git",
                    "referenceLocator": "https://github.com/memfault/memfault-firmware-sdk.git",
                }
            ],
        }
        spdx_doc["packages"].append(main_package)

        # Document describes main package
        spdx_doc["relationships"].append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": main_package_id,
            }
        )

        # Add relationships between main package and files
        for file_path, file_id in file_ids.items():
            spdx_doc["relationships"].append(
                {
                    "spdxElementId": main_package_id,
                    "relationshipType": "CONTAINS",
                    "relatedSpdxElement": file_id,
                }
            )

        # Component packages
        component_ids = {}
        for comp_name, comp_data in self.components.items():
            comp_id = self.generate_spdx_id()
            component_ids[comp_name] = comp_id

            # Determine primary license
            licenses = comp_data.get("licenses", ["NOASSERTION"])
            primary_license = licenses[0] if licenses else "NOASSERTION"

            component_pkg = {
                "SPDXID": comp_id,
                "name": f"memfault-sdk-{comp_name}",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": True,
                "versionInfo": version_info["version"],
                "supplier": "Organization: Memfault",
                "licenseConcluded": primary_license,
                "licenseDeclared": primary_license,
                "copyrightText": "Copyright (c) Memfault, Inc.",
                "description": comp_data.get(
                    "description", f"Memfault SDK {comp_name} component"
                ),
            }
            spdx_doc["packages"].append(component_pkg)

            # Relationship: main package contains component
            spdx_doc["relationships"].append(
                {
                    "spdxElementId": main_package_id,
                    "relationshipType": "CONTAINS",
                    "relatedSpdxElement": comp_id,
                }
            )

            # Add relationships between component and its files
            for file_info in comp_data.get("source_files", []) + comp_data.get(
                "header_files", []
            ):
                file_path = file_info["path"]
                if file_path in file_ids:
                    spdx_doc["relationships"].append(
                        {
                            "spdxElementId": comp_id,
                            "relationshipType": "CONTAINS",
                            "relatedSpdxElement": file_ids[file_path],
                        }
                    )

        # External dependencies
        for dep in self.external_deps:
            if dep and not dep.startswith("memfault"):  # Skip internal includes
                dep_id = self.generate_spdx_id()

                dep_pkg = {
                    "SPDXID": dep_id,
                    "name": dep,
                    "downloadLocation": "NOASSERTION",
                    "filesAnalyzed": False,
                    "licenseConcluded": "NOASSERTION",
                    "licenseDeclared": "NOASSERTION",
                    "copyrightText": "NOASSERTION",
                    "description": f"External dependency: {dep}",
                }
                spdx_doc["packages"].append(dep_pkg)

                # Relationship: main package depends on external dependency
                spdx_doc["relationships"].append(
                    {
                        "spdxElementId": main_package_id,
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": dep_id,
                    }
                )

        return spdx_doc

    def generate_tag_value_spdx(self) -> str:
        """Generate SPDX document in tag-value format."""
        json_doc = self.generate_json_spdx()
        lines = []

        # Document section
        lines.extend(
            [
                f"SPDXVersion: {json_doc['spdxVersion']}",
                f"DataLicense: {json_doc['dataLicense']}",
                f"SPDXID: {json_doc['SPDXID']}",
                f"DocumentName: {json_doc['name']}",
                f"DocumentNamespace: {json_doc['documentNamespace']}",
                f"Creator: {json_doc['creationInfo']['creators'][0]}",
                f"Created: {json_doc['creationInfo']['created']}",
                "",
            ]
        )

        # Files section
        if "files" in json_doc:
            for file_entry in json_doc["files"]:
                lines.extend(
                    [
                        f"FileName: {file_entry['fileName']}",
                        f"SPDXID: {file_entry['SPDXID']}",
                        f"FileChecksum: {file_entry['checksums'][0]['algorithm']}: {file_entry['checksums'][0]['value']}",
                        f"LicenseConcluded: {file_entry['licenseConcluded']}",
                        f"FileCopyrightText: {file_entry['copyrightText']}",
                        "",
                    ]
                )

        # Packages
        for pkg in json_doc["packages"]:
            lines.extend(
                [
                    f"PackageName: {pkg['name']}",
                    f"SPDXID: {pkg['SPDXID']}",
                    f"PackageDownloadLocation: {pkg['downloadLocation']}",
                    f"FilesAnalyzed: {str(pkg['filesAnalyzed']).lower()}",
                    f"PackageLicenseConcluded: {pkg['licenseConcluded']}",
                    f"PackageLicenseDeclared: {pkg['licenseDeclared']}",
                    f"PackageCopyrightText: {pkg['copyrightText']}",
                    f"PackageDescription: {pkg['description']}",
                    "",
                ]
            )

            if "versionInfo" in pkg:
                lines.insert(-1, f"PackageVersionInfo: {pkg['versionInfo']}")
            if "supplier" in pkg:
                lines.insert(-1, f"PackageSupplier: {pkg['supplier']}")
            if "homepage" in pkg:
                lines.insert(-1, f"PackageHomePage: {pkg['homepage']}")

        # Relationships
        for rel in json_doc["relationships"]:
            lines.append(
                f"Relationship: {rel['spdxElementId']} {rel['relationshipType']} {rel['relatedSpdxElement']}"
            )

        return "\n".join(lines)


def main():
    """Main function to generate SBOM."""
    parser = argparse.ArgumentParser(
        description="Generate SPDX SBOM for Memfault Firmware SDK"
    )
    parser.add_argument(
        "--output-file",
        "-o",
        default="memfault-sdk-sbom.spdx",
        help="Output file name (default: memfault-sdk-sbom.spdx)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "tag", "yaml"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--sdk-root",
        default=".",
        help="Path to SDK root directory (default: current directory)",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        action="append",
        default=[],
        help="Additional directories to exclude from scanning (can be used multiple times). Default excludes: examples, tests, .git, __pycache__, build, dist, .vscode, .idea",
    )

    args = parser.parse_args()

    # Validate SDK root
    sdk_root = Path(args.sdk_root).resolve()
    if not (sdk_root / "components").exists():
        print(f"Error: {sdk_root} does not appear to be Memfault SDK root directory")
        sys.exit(1)

    print("Analyzing Memfault Firmware SDK...")

    # Initialize analyzers
    license_detector = LicenseDetector()
    file_analyzer = FileAnalyzer(license_detector)
    component_analyzer = ComponentAnalyzer(sdk_root, file_analyzer)

    # Analyze components
    print("Scanning components...")
    component_analyzer.analyze_all_components(args.exclude)

    # Generate SPDX
    print("Generating SPDX document...")
    spdx_generator = SPDXGenerator(
        sdk_root, component_analyzer.components, component_analyzer.external_deps
    )

    # Generate in requested format
    if args.format == "json":
        spdx_doc = spdx_generator.generate_json_spdx()
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(spdx_doc, f, indent=2, ensure_ascii=False)
    elif args.format == "yaml":
        spdx_doc = spdx_generator.generate_json_spdx()
        with open(args.output_file, "w", encoding="utf-8") as f:
            yaml.dump(spdx_doc, f, default_flow_style=False, allow_unicode=True)
    elif args.format == "tag":
        spdx_content = spdx_generator.generate_tag_value_spdx()
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(spdx_content)

    # Print summary
    print(f"\nSBOM generated successfully: {args.output_file}")
    print(f"Format: SPDX {args.format.upper()}")
    print(f"Components analyzed: {len(component_analyzer.components)}")
    print(f"External dependencies found: {len(component_analyzer.external_deps)}")

    # Show some statistics
    total_files = sum(
        len(comp.get("source_files", [])) + len(comp.get("header_files", []))
        for comp in component_analyzer.components.values()
    )
    print(f"Total files analyzed: {total_files}")

    if component_analyzer.external_deps:
        print(
            f"External dependencies: {', '.join(sorted(component_analyzer.external_deps))}"
        )


if __name__ == "__main__":
    main()
