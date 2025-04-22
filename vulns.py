from typing import List
import httpx
import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("vulnerabilities")

# Constants
OSV_QUERY_API = "https://api.osv.dev/v1/query"
USER_AGENT = "vulns-app/1.0"


async def query_vulns(
    package_name: str, ecosystem: str, version: str = None
) -> List[dict[str, str]] | None:
    """Make a request to the OSV API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            payload = {"package": {"name": package_name, "ecosystem": ecosystem}}
            if version:
                payload["version"] = version
            response = await client.post(
                OSV_QUERY_API, json=payload, headers=headers, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_date(date_str: str) -> str:
    """Format ISO date string to a more readable format."""
    try:
        # Parse the ISO format date
        date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Format it in a more readable way
        return date_obj.strftime("%B %d, %Y")
    except Exception:
        return date_str

def format_vuln(vuln: dict) -> str:
    """Format a vulnerability into a readable string."""

    # Start building the output text
    output = []

    # Vulnerability ID and aliases
    output.append(f"Vulnerability ID: {vuln['id']}")
    if 'aliases' in vuln and vuln['aliases']:
        output.append(f"Also known as: {', '.join(vuln['aliases'])}")

    # Publication and modification dates
    if 'published' in vuln:
        output.append(f"Published: {format_date(vuln['published'])}")
    if 'modified' in vuln:
        output.append(f"Last modified: {format_date(vuln['modified'])}")

    # Description
    if 'details' in vuln:
        output.append(f"\nDescription:\n{vuln['details']}")

    # Affected packages
    if 'affected' in vuln and vuln['affected']:
        output.append("\nAffected Packages:")
        for affected in vuln['affected']:
            pkg = affected.get('package', {})
            output.append(f"- {pkg.get('name', 'Unknown')} ({pkg.get('ecosystem', 'Unknown')})")

            # Affected versions
            if 'versions' in affected and affected['versions']:
                output.append(f"  Affected versions: {', '.join(affected['versions'])}")

            # Fixed versions
            fixed_versions = []
            for range_info in affected.get('ranges', []):
                for event in range_info.get('events', []):
                    if 'fixed' in event:
                        fixed_versions.append(event['fixed'])

            if fixed_versions:
                output.append(f"  Fixed in versions: {', '.join(fixed_versions)}")

    # References
    if 'references' in vuln and vuln['references']:
        output.append("\nReferences:")
        for ref in vuln['references']:
            ref_type = ref.get('type', 'Unknown')
            url = ref.get('url', 'No URL provided')
            output.append(f"- {ref_type}: {url}")

    return "\n".join(output)


@mcp.tool()
async def query_vulnerabilities(package_name: str, ecosystem: str, version: str = None) -> str:
    """
    Get vulnerabilities for a package from an ecosystem.

    Args:
        package_name (str): Name of the package
        ecosystem (str): Package ecosystem (PyPI, npm, etc.)
        version (str, optional): Specific version to check
    """
    data = await query_vulns(package_name, ecosystem, version)

    if not data or "vulns" not in data:
        return "Unable to fetch vulnerabilities or no vulnerabilities found."

    vulns = [format_vuln(vuln) for vuln in data["vulns"]]
    return "\n---\n".join(vulns)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
