"""
Healthcare Code Knowledge Base Downloader
Downloads ICD-10, CPT, HCPCS, NCCI, DRG, and CARC/RARC codes from CMS.gov and other sources.
"""
import asyncio
import aiohttp
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class CodeDownloader:
    """Downloads and manages healthcare code sets."""

    def __init__(self, output_dir: str = "./data/knowledge"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),
            headers={'User-Agent': 'Aethera-AI/1.0'}
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def download_icd10(self) -> Dict:
        """
        Download ICD-10-CM diagnosis codes.
        Source: CMS.gov
        """
        print("Downloading ICD-10-CM codes...")

        # CMS provides ICD-10-CM as CSV download
        url = "https://www.cms.gov/files/zip/icd-10-cm-csv-files.zip"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {'success': False, 'error': f"HTTP {resp.status}"}

                # Save the file
                output_path = self.output_dir / "icd10-cm.zip"
                with open(output_path, 'wb') as f:
                    f.write(await resp.read())

                # Note: Would need to unzip and parse in production
                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'CMS.gov'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_cpt(self) -> Dict:
        """
        Download CPT codes.
        Note: CPT codes are copyrighted by AMA and require licensing.
        This provides a structure for licensed users.
        """
        print("CPT codes require AMA licensing - skipping automatic download")

        # Create placeholder for licensed CPT data
        output_path = self.output_dir / "cpt-codes.json"
        placeholder = {
            'notice': 'CPT codes are copyrighted by the American Medical Association',
            'license_required': True,
            'license_info': 'https://www.ama-assn.org/practice-management/cpt',
            'codes': []  # Would be populated with licensed data
        }

        with open(output_path, 'w') as f:
            json.dump(placeholder, f, indent=2)

        return {
            'success': True,
            'path': str(output_path),
            'timestamp': datetime.now().isoformat(),
            'note': 'AMA license required for actual codes'
        }

    async def download_hcpcs(self) -> Dict:
        """
        Download HCPCS Level II codes.
        Source: CMS.gov
        """
        print("Downloading HCPCS Level II codes...")

        url = "https://www.cms.gov/files/zip/hcpcs-csv-files.zip"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {'success': False, 'error': f"HTTP {resp.status}"}

                output_path = self.output_dir / "hcpcs-level2.zip"
                with open(output_path, 'wb') as f:
                    f.write(await resp.read())

                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'CMS.gov'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_ncci(self) -> Dict:
        """
        Download NCCI edit files.
        Source: CMS.gov
        """
        print("Downloading NCCI edits...")

        # NCCI edits are quarterly releases
        year = datetime.now().year
        quarter = ((datetime.now().month - 1) // 3) + 1

        # PTN (Procedure-to-Procedure) edits
        url = f"https://www.cms.gov/files/zip/ncci-ptn-edits-{year}-q{quarter}.zip"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    # Try previous quarter
                    q = quarter - 1 if quarter > 1 else 4
                    y = year if quarter > 1 else year - 1
                    url = f"https://www.cms.gov/files/zip/ncci-ptn-edits-{y}-q{q}.zip"
                    async with self.session.get(url) as resp2:
                        if resp2.status != 200:
                            return {'success': False, 'error': f"HTTP {resp2.status}"}
                        resp = resp2

                output_path = self.output_dir / f"ncci-edits-{year}-q{quarter}.zip"
                with open(output_path, 'wb') as f:
                    f.write(await resp.read())

                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'CMS.gov',
                    'quarter': f"Q{quarter} {year}"
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_drg(self) -> Dict:
        """
        Download DRG (MS-DRG) definitions.
        Source: CMS.gov
        """
        print("Downloading MS-DRG definitions...")

        url = "https://www.cms.gov/files/zip/ms-drg-definitions.zip"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {'success': False, 'error': f"HTTP {resp.status}"}

                output_path = self.output_dir / "ms-drg-definitions.zip"
                with open(output_path, 'wb') as f:
                    f.write(await resp.read())

                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'CMS.gov'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_carc_rarc(self) -> Dict:
        """
        Download CARC and RARC codes.
        Source: Washington Publishing Company (WPC)
        """
        print("Downloading CARC/RARC codes...")

        # CARC codes
        carc_url = "https://www.wpc-edi.com/media/codes/claim-adjustment-reason-codes/"

        try:
            async with self.session.get(carc_url) as resp:
                if resp.status != 200:
                    return {'success': False, 'error': f"HTTP {resp.status}"}

                # Parse HTML table (simplified - would use BeautifulSoup in production)
                html = await resp.text()

                # Save raw HTML for processing
                output_path = self.output_dir / "carc-codes.html"
                with open(output_path, 'w') as f:
                    f.write(html)

                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'WPC-EDI'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_ndc(self) -> Dict:
        """
        Download NDC (National Drug Code) database.
        Source: FDA
        """
        print("Downloading NDC database...")

        url = "https://www.fda.gov/files/drugs/published/National-Drug-Code-Database-API-Documentation.zip"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {'success': False, 'error': f"HTTP {resp.status}"}

                output_path = self.output_dir / "ndc-database.zip"
                with open(output_path, 'wb') as f:
                    f.write(await resp.read())

                return {
                    'success': True,
                    'path': str(output_path),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'FDA'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def download_loinc(self) -> Dict:
        """
        Download LOINC codes.
        Source: Regenstrief Institute
        Note: Requires accepting license agreement
        """
        print("LOINC codes require license agreement - skipping automatic download")

        output_path = self.output_dir / "loinc-codes.json"
        placeholder = {
            'notice': 'LOINC is copyrighted by Regenstrief Institute, Inc.',
            'license_required': True,
            'license_info': 'https://loinc.org/license/',
            'download_url': 'https://loinc.org/downloads'
        }

        with open(output_path, 'w') as f:
            json.dump(placeholder, f, indent=2)

        return {
            'success': True,
            'path': str(output_path),
            'timestamp': datetime.now().isoformat(),
            'note': 'License agreement required for actual codes'
        }

    async def download_snomed(self) -> Dict:
        """
        Download SNOMED CT codes.
        Source: SNOMED International
        Note: Requires SNOMED International membership/license
        """
        print("SNOMED CT requires license - skipping automatic download")

        output_path = self.output_dir / "snomed-ct.json"
        placeholder = {
            'notice': 'SNOMED CT is copyrighted by SNOMED International',
            'license_required': True,
            'license_info': 'https://www.snomed.org/get-snomed',
            'us_extension': 'https://www.snomed.org/us-extension'
        }

        with open(output_path, 'w') as f:
            json.dump(placeholder, f, indent=2)

        return {
            'success': True,
            'path': str(output_path),
            'timestamp': datetime.now().isoformat(),
            'note': 'SNOMED International license required'
        }

    async def download_all(self) -> Dict:
        """Download all available code sets."""
        results = {}

        await self.initialize()

        try:
            # Free downloads
            results['icd10'] = await self.download_icd10()
            results['hcpcs'] = await self.download_hcpcs()
            results['ncci'] = await self.download_ncci()
            results['drg'] = await self.download_drg()
            results['carc_rarc'] = await self.download_carc_rarc()
            results['ndc'] = await self.download_ndc()

            # Licensed downloads (create placeholders)
            results['cpt'] = await self.download_cpt()
            results['loinc'] = await self.download_loinc()
            results['snomed'] = await self.download_snomed()

            # Save summary
            summary_path = self.output_dir / "download-summary.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': results
                }, f, indent=2)

            return {
                'success': True,
                'summary': str(summary_path),
                'results': results
            }
        finally:
            await self.close()


async def main():
    """Main entry point for downloading codes."""
    downloader = CodeDownloader()
    results = await downloader.download_all()

    print("\nDownload Summary:")
    print("=" * 50)
    for code_set, result in results.items():
        status = "✓" if result.get('success') else "✗"
        print(f"{status} {code_set}: {result.get('path', result.get('error', 'Unknown'))}")


if __name__ == "__main__":
    asyncio.run(main())
