# SRC2PURL Examples

This document provides common use cases and workflows for SRC2PURL.

## Table of Contents

1. [Basic Examples](#basic-examples)
2. [Real-World Scenarios](#real-world-scenarios)
3. [Integration Examples](#integration-examples)
4. [Advanced Workflows](#advanced-workflows)
5. [Troubleshooting Examples](#troubleshooting-examples)

## Basic Examples

### Identifying a Simple Node.js Project

```bash
# Project structure:
# my-app/
#   ├── package.json
#   ├── index.js
#   └── src/

$ src2purl ./my-app

Package: my-app
Version: 1.0.0
PURL: pkg:npm/my-app@1.0.0
License: MIT
Confidence: 95%
Ecosystem: npm
```

### Python Project Identification

```bash
# Project with setup.py
$ src2purl ./python-project

Package: requests
Version: 2.28.0
PURL: pkg:pypi/requests@2.28.0
License: Apache-2.0
Confidence: 92%
```

### Java/Maven Project

```bash
# Project with pom.xml
$ src2purl ./java-project

Package: commons-lang3
Version: 3.12.0
PURL: pkg:maven/org.apache.commons/commons-lang3@3.12.0
License: Apache-2.0
Confidence: 88%
```

## Real-World Scenarios

### Scenario 1: Identifying a Cloned GitHub Repository

```bash
# Clone a repository
$ git clone https://github.com/expressjs/express.git
$ cd express

# Identify the package
$ src2purl .

Package: express
Version: 4.18.2
PURL: pkg:npm/express@4.18.2
Repository: https://github.com/expressjs/express
License: MIT
Confidence: 98%

# With detailed output
$ src2purl . --verbose

[INFO] Starting package identification...
[INFO] Found package.json at ./package.json
[INFO] Extracted from manifest: express@4.18.2
[INFO] Validating with GitHub API...
[INFO] Repository confirmed: expressjs/express
[INFO] Cross-validation successful
[INFO] Final confidence: 98%
```

### Scenario 2: Analyzing a Monorepo

```bash
# Lerna/Yarn workspace structure
# monorepo/
#   ├── package.json (workspace root)
#   ├── packages/
#   │   ├── package-a/
#   │   │   └── package.json
#   │   └── package-b/
#   │       └── package.json

$ src2purl ./monorepo --detect-subcomponents

Main Package: my-monorepo
Version: 1.0.0
PURL: pkg:npm/my-monorepo@1.0.0

Subcomponents detected:
  - package-a@2.1.0 (pkg:npm/package-a@2.1.0)
  - package-b@1.5.3 (pkg:npm/package-b@1.5.3)
```

### Scenario 3: Security Audit with Software Heritage

```bash
# Comprehensive security analysis
$ export SWH_API_TOKEN=your_token
$ src2purl ./unknown-source --use-swh --verbose

[INFO] Computing SWHID for directory...
[INFO] SWHID: swh:1:dir:94a9ed024d3859793618152ea559a168bbcbb5e2
[INFO] Querying Software Heritage archive...
[INFO] Found in archive: visited 2021-03-15
[INFO] Known occurrences: 3
[INFO] Origin: https://github.com/lodash/lodash
[INFO] Detected: lodash@4.17.21
[INFO] Security notice: Known vulnerabilities in prototype pollution

Package: lodash
Version: 4.17.21
PURL: pkg:npm/lodash@4.17.21
First seen: 2021-03-15
Archive status: Preserved
Confidence: 94%
```

### Scenario 4: Identifying Modified Open Source

```bash
# Project with modified source code
$ src2purl ./modified-react

[WARNING] Exact match not found, using similarity matching
[INFO] Best match: react@18.2.0 (87% similarity)

Package: react (modified)
Original Version: 18.2.0
PURL: pkg:npm/react@18.2.0
License: MIT
Confidence: 87%
Notes: Source appears to be modified from original
```

## Integration Examples

### Integration with CI/CD Pipeline

#### GitHub Actions Workflow

```yaml
name: Package Analysis

on: [push, pull_request]

jobs:
  identify-packages:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install SRC2PURL
        run: pip install src2purl

      - name: Identify Package
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          src2purl . --output-format json -o package-info.json

      - name: Upload Package Info
        uses: actions/upload-artifact@v3
        with:
          name: package-identification
          path: package-info.json

      - name: Check License Compliance
        run: |
          python -c "
          import json
          with open('package-info.json') as f:
              data = json.load(f)
          allowed = ['MIT', 'Apache-2.0', 'BSD-3-Clause']
          if data['license'] not in allowed:
              raise ValueError(f'License {data['license']} not allowed')
          print(f'✓ License {data['license']} is compliant')
          "
```

### Integration with SEMCL.ONE Ecosystem

```python
#!/usr/bin/env python3
"""
Complete SEMCL.ONE workflow for package analysis
"""

from src2purl import identify_package
from purl2src import get_download_url
from osslili import detect_licenses
from purl2notices import generate_notices
import requests
import tarfile
import tempfile

def analyze_package(source_path):
    """Complete package analysis workflow"""

    # Step 1: Identify the package
    print("Identifying package...")
    package = identify_package(source_path)
    print(f"Found: {package.purl}")

    # Step 2: Get source download URL
    print("Getting source URL...")
    download_url = get_download_url(package.purl)
    print(f"Source URL: {download_url}")

    # Step 3: Download and extract source
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download source archive
        response = requests.get(download_url)
        archive_path = f"{tmpdir}/source.tar.gz"
        with open(archive_path, 'wb') as f:
            f.write(response.content)

        # Extract archive
        with tarfile.open(archive_path) as tar:
            tar.extractall(tmpdir)

        # Step 4: Detect licenses
        print("Detecting licenses...")
        licenses = detect_licenses(tmpdir)
        print(f"Licenses found: {licenses}")

        # Step 5: Generate notices
        print("Generating notices...")
        notices = generate_notices(package.purl)
        with open("NOTICES.txt", "w") as f:
            f.write(notices)

    return {
        'package': package.to_dict(),
        'download_url': download_url,
        'licenses': licenses,
        'notices_generated': True
    }

if __name__ == "__main__":
    import sys
    result = analyze_package(sys.argv[1])
    print("\nAnalysis complete:")
    print(json.dumps(result, indent=2))
```

### Docker-based Analysis

```dockerfile
# Dockerfile for SRC2PURL analysis
FROM python:3.9-slim

# Install dependencies
RUN pip install src2purl osslili purl2notices

# Add analysis script
COPY analyze.py /app/analyze.py

# Set working directory
WORKDIR /workspace

# Run analysis
ENTRYPOINT ["python", "/app/analyze.py"]
```

```bash
# Build and run
$ docker build -t src2purl-analyzer .
$ docker run -v $(pwd):/workspace src2purl-analyzer .
```

## Advanced Workflows

### Batch Processing Multiple Projects

```python
#!/usr/bin/env python3
"""
Batch process multiple projects and generate report
"""

import os
import json
from pathlib import Path
from src2purl import identify_package
import pandas as pd

def batch_analyze(root_dir):
    """Analyze all projects in a directory"""
    results = []

    # Find all projects (containing package.json, setup.py, etc.)
    for path in Path(root_dir).rglob("*"):
        if path.name in ["package.json", "setup.py", "pom.xml", "go.mod"]:
            project_dir = path.parent

            try:
                print(f"Analyzing {project_dir}...")
                result = identify_package(str(project_dir))

                results.append({
                    'path': str(project_dir),
                    'name': result.name,
                    'version': result.version,
                    'purl': result.purl,
                    'license': result.license,
                    'confidence': result.confidence,
                    'ecosystem': result.ecosystem
                })
            except Exception as e:
                print(f"Error analyzing {project_dir}: {e}")
                results.append({
                    'path': str(project_dir),
                    'error': str(e)
                })

    return results

def generate_report(results):
    """Generate analysis report"""

    # Create DataFrame
    df = pd.DataFrame(results)

    # Summary statistics
    print("\n=== Analysis Summary ===")
    print(f"Total projects: {len(df)}")
    print(f"Successful: {len(df[~df['name'].isna()])}")
    print(f"Failed: {len(df[df['name'].isna()])}")

    # License distribution
    print("\n=== License Distribution ===")
    license_counts = df['license'].value_counts()
    for license, count in license_counts.items():
        print(f"{license}: {count}")

    # Ecosystem distribution
    print("\n=== Ecosystem Distribution ===")
    ecosystem_counts = df['ecosystem'].value_counts()
    for ecosystem, count in ecosystem_counts.items():
        print(f"{ecosystem}: {count}")

    # Export to CSV
    df.to_csv("analysis_report.csv", index=False)
    print("\nReport saved to analysis_report.csv")

    # Export to JSON
    with open("analysis_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Report saved to analysis_report.json")

if __name__ == "__main__":
    import sys
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    results = batch_analyze(root_dir)
    generate_report(results)
```

### Custom Discovery Strategy

```python
#!/usr/bin/env python3
"""
Custom discovery strategy with fallback mechanisms
"""

from src2purl import identify_package
from src2purl.discovery import HashBasedDiscovery, ManifestDiscovery
import time

class CustomDiscoveryStrategy:
    def __init__(self):
        self.methods = [
            ("manifest", self.try_manifest),
            ("github", self.try_github),
            ("scanoss", self.try_scanoss),
            ("swh", self.try_swh)
        ]

    def identify(self, path):
        """Try multiple discovery methods with fallback"""
        results = []

        for name, method in self.methods:
            print(f"Trying {name} discovery...")
            start = time.time()

            try:
                result = method(path)
                elapsed = time.time() - start

                if result and result.confidence > 0:
                    results.append({
                        'method': name,
                        'result': result,
                        'time': elapsed,
                        'confidence': result.confidence
                    })

                    # Stop if high confidence
                    if result.confidence > 0.9:
                        print(f"High confidence match found with {name}")
                        break

            except Exception as e:
                print(f"Method {name} failed: {e}")

        # Return best result
        if results:
            best = max(results, key=lambda x: x['confidence'])
            return best['result']

        return None

    def try_manifest(self, path):
        """Try manifest-based discovery"""
        return identify_package(
            path,
            use_swh=False,
            max_depth=1
        )

    def try_github(self, path):
        """Try GitHub-based discovery"""
        return identify_package(
            path,
            use_swh=False,
            confidence_threshold=0.5
        )

    def try_scanoss(self, path):
        """Try SCANOSS fingerprinting"""
        return identify_package(
            path,
            use_swh=False,
            confidence_threshold=0.3
        )

    def try_swh(self, path):
        """Try Software Heritage (slow but comprehensive)"""
        return identify_package(
            path,
            use_swh=True,
            confidence_threshold=0.2
        )

# Usage
strategy = CustomDiscoveryStrategy()
result = strategy.identify("/path/to/project")
if result:
    print(f"Identified: {result.purl}")
else:
    print("Could not identify package")
```

## Troubleshooting Examples

### Debug API Issues

```bash
# Enable debug logging
$ export SRC2PURL_DEBUG=1
$ src2purl ./project --verbose

[DEBUG] GitHub API request: GET /search/code
[DEBUG] Response: 403 Forbidden
[ERROR] GitHub rate limit exceeded
[INFO] Falling back to SCANOSS...
```

### Handle Network Issues

```python
#!/usr/bin/env python3
"""
Robust identification with retry logic
"""

import time
from src2purl import identify_package

def identify_with_retry(path, max_retries=3):
    """Identify package with retry logic"""

    for attempt in range(max_retries):
        try:
            # Try identification
            result = identify_package(path)
            return result

        except ConnectionError as e:
            print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # Exponential backoff
                print(f"Waiting {wait} seconds before retry...")
                time.sleep(wait)
            else:
                print("Max retries reached, using offline mode")
                # Try offline mode (manifest only)
                return identify_package(
                    path,
                    no_cache=False,  # Use cache
                    use_swh=False    # No network calls
                )

        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

# Usage
result = identify_with_retry("/path/to/project")
```

### Validate Results

```python
#!/usr/bin/env python3
"""
Validate identification results
"""

from src2purl import identify_package
import requests

def validate_identification(path):
    """Validate package identification"""

    # Get identification
    result = identify_package(path)

    validations = {
        'purl_valid': False,
        'version_exists': False,
        'license_valid': False,
        'source_accessible': False
    }

    # Validate PURL format
    try:
        from packageurl import PackageURL
        purl = PackageURL.from_string(result.purl)
        validations['purl_valid'] = True
    except:
        pass

    # Check if version exists in registry
    if result.ecosystem == 'npm':
        response = requests.get(
            f"https://registry.npmjs.org/{result.name}"
        )
        if response.ok:
            data = response.json()
            validations['version_exists'] = (
                result.version in data.get('versions', {})
            )

    # Validate license
    from src2purl.licenses import SPDX_LICENSES
    validations['license_valid'] = (
        result.license in SPDX_LICENSES
    )

    # Check source accessibility
    from purl2src import get_download_url
    try:
        url = get_download_url(result.purl)
        response = requests.head(url)
        validations['source_accessible'] = response.ok
    except:
        pass

    return result, validations

# Usage
result, validations = validate_identification("/path/to/project")
print(f"Package: {result.purl}")
print(f"Validations: {validations}")
```

## Performance Optimization Examples

### Parallel Processing

```python
#!/usr/bin/env python3
"""
Process multiple projects in parallel
"""

from concurrent.futures import ProcessPoolExecutor
from src2purl import identify_package
import os

def process_project(project_path):
    """Process single project"""
    try:
        result = identify_package(project_path)
        return {
            'success': True,
            'path': project_path,
            'purl': result.purl,
            'confidence': result.confidence
        }
    except Exception as e:
        return {
            'success': False,
            'path': project_path,
            'error': str(e)
        }

def parallel_analyze(project_dirs, max_workers=4):
    """Analyze projects in parallel"""

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_project, path): path
            for path in project_dirs
        }

        # Collect results
        results = []
        for future in futures:
            try:
                result = future.result(timeout=60)
                results.append(result)
                if result['success']:
                    print(f"✓ {result['path']}: {result['purl']}")
                else:
                    print(f"✗ {result['path']}: {result['error']}")
            except TimeoutError:
                print(f"⧖ {futures[future]}: Timeout")

    return results

# Usage
projects = [
    "/path/to/project1",
    "/path/to/project2",
    "/path/to/project3"
]
results = parallel_analyze(projects)
```

### Caching Strategy

```python
#!/usr/bin/env python3
"""
Implement intelligent caching
"""

import hashlib
import json
from pathlib import Path
from src2purl import identify_package

class SmartCache:
    def __init__(self, cache_dir="~/.cache/src2purl"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, path, options):
        """Generate cache key from path and options"""
        # Include file hashes in cache key
        file_hashes = self._hash_directory(path)
        key_data = {
            'path': str(path),
            'options': options,
            'file_hashes': file_hashes
        }
        key = hashlib.sha256(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()
        return key

    def _hash_directory(self, path):
        """Hash key files in directory"""
        key_files = [
            'package.json', 'setup.py', 'pom.xml',
            'go.mod', 'Cargo.toml', 'composer.json'
        ]
        hashes = {}
        for file in key_files:
            file_path = Path(path) / file
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    hashes[file] = hashlib.md5(f.read()).hexdigest()
        return hashes

    def get(self, path, options):
        """Get cached result if valid"""
        key = self.get_cache_key(path, options)
        cache_file = self.cache_dir / f"{key}.json"

        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return None

    def set(self, path, options, result):
        """Cache result"""
        key = self.get_cache_key(path, options)
        cache_file = self.cache_dir / f"{key}.json"

        with open(cache_file, 'w') as f:
            json.dump(result.to_dict(), f)

# Usage
cache = SmartCache()
path = "/path/to/project"
options = {'use_swh': False, 'confidence_threshold': 0.5}

# Check cache
cached = cache.get(path, options)
if cached:
    print(f"Using cached result: {cached['purl']}")
else:
    # Identify and cache
    result = identify_package(path, **options)
    cache.set(path, options, result)
    print(f"New identification: {result.purl}")
```