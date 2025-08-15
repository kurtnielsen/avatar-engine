#!/usr/bin/env python3
"""
RTM-based sampling audit runner that combines both approaches.
Samples specific requirements and validates their implementation.
"""
import json
import random
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import re

class RTMSamplingAuditor:
    def __init__(self, rtm_path: str, docs_root: str = "docs"):
        self.rtm_path = rtm_path
        self.docs_root = Path(docs_root)
        self.requirements = []
        
    def parse_rtm_table(self) -> List[Dict[str, Any]]:
        """Parse RTM markdown table format."""
        content = Path(self.rtm_path).read_text()
        requirements = []
        
        # Find requirement entries in various formats
        patterns = [
            # Table format: | FR-1.1 | Description | Tech Ref | Arch Ref |
            re.compile(r'\|\s*\[?(\w+-\d+(?:\.\d+)?)\]?\s*\|([^|]+)\|([^|]+)\|([^|]+)\|'),
            # List format: - **FR-1.1**: Description
            re.compile(r'^[-*]\s*\*?\*?(\w+-\d+(?:\.\d+)?)\*?\*?:?\s*(.+)$', re.MULTILINE)
        ]
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                if pattern.groups == 4:
                    req_id, desc, tech_ref, arch_ref = match.groups()
                    requirements.append({
                        'id': req_id.strip(),
                        'description': desc.strip(),
                        'tech_ref': tech_ref.strip(),
                        'arch_ref': arch_ref.strip()
                    })
                else:
                    req_id, desc = match.groups()
                    requirements.append({
                        'id': req_id.strip(),
                        'description': desc.strip(),
                        'tech_ref': 'Not specified',
                        'arch_ref': 'Not specified'
                    })
        
        return requirements
    
    def sample_requirements(self, fr_count: int = 5, nfr_count: int = 5) -> List[Dict[str, Any]]:
        """Sample random requirements for audit."""
        if not self.requirements:
            self.requirements = self.parse_rtm_table()
        
        fr_reqs = [r for r in self.requirements if r['id'].startswith('FR')]
        nfr_reqs = [r for r in self.requirements if r['id'].startswith('NFR')]
        
        # Random sampling
        fr_sample = random.sample(fr_reqs, min(fr_count, len(fr_reqs)))
        nfr_sample = random.sample(nfr_reqs, min(nfr_count, len(nfr_reqs)))
        
        return fr_sample + nfr_sample
    
    def validate_requirement(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single requirement implementation."""
        findings = {
            'requirement': req,
            'validation': {
                'rtm_complete': True,
                'implementation_found': False,
                'test_coverage': False,
                'documentation': False
            },
            'issues': [],
            'recommendations': []
        }
        
        # Check RTM completeness
        if 'Gap' in req['tech_ref'] or 'TBD' in req['tech_ref']:
            findings['validation']['rtm_complete'] = False
            findings['issues'].append(f"Technical specification missing for {req['id']}")
            findings['recommendations'].append("Complete technical specification mapping")
        
        if 'Gap' in req['arch_ref'] or 'TBD' in req['arch_ref']:
            findings['validation']['rtm_complete'] = False
            findings['issues'].append(f"Architecture reference missing for {req['id']}")
            findings['recommendations'].append("Add architecture documentation")
        
        # Check for implementation references
        if req['tech_ref'] and 'Not specified' not in req['tech_ref']:
            # Extract file references
            file_refs = re.findall(r'`([^`]+\.(py|js|ts))`', req['tech_ref'])
            if file_refs:
                findings['validation']['implementation_found'] = True
                findings['implementation_files'] = [f[0] for f in file_refs]
                
                # Verify files exist
                for file_ref in findings['implementation_files']:
                    if not Path(file_ref).exists():
                        findings['issues'].append(f"Referenced file not found: {file_ref}")
        
        # Requirement-specific checks
        if req['id'].startswith('NFR') and 'performance' in req['description'].lower():
            findings['recommendations'].append("Add performance benchmarks and monitoring")
        
        if req['id'].startswith('NFR') and 'security' in req['description'].lower():
            findings['recommendations'].append("Implement security scanning in CI/CD")
        
        return findings
    
    def generate_audit_report(self, sample: List[Dict[str, Any]], agent: str = "local") -> Dict[str, Any]:
        """Generate complete audit report from sampled requirements."""
        validations = [self.validate_requirement(req) for req in sample]
        
        # Calculate metrics
        total_reqs = len(validations)
        complete_rtm = sum(1 for v in validations if v['validation']['rtm_complete'])
        implemented = sum(1 for v in validations if v['validation']['implementation_found'])
        
        # Aggregate issues and recommendations
        all_issues = []
        all_recommendations = []
        for v in validations:
            all_issues.extend(v['issues'])
            all_recommendations.extend(v['recommendations'])
        
        # Remove duplicates
        all_issues = list(set(all_issues))
        all_recommendations = list(set(all_recommendations))
        
        # Determine grade based on findings
        completeness = (complete_rtm + implemented) / (total_reqs * 2) * 100
        if completeness >= 90:
            grade = 'A'
        elif completeness >= 80:
            grade = 'B'
        elif completeness >= 70:
            grade = 'C'
        elif completeness >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        report = {
            'metadata': {
                'agent': agent,
                'timestamp': datetime.now().isoformat(),
                'rtm_path': self.rtm_path,
                'sample_size': {
                    'fr': sum(1 for r in sample if r['id'].startswith('FR')),
                    'nfr': sum(1 for r in sample if r['id'].startswith('NFR'))
                }
            },
            'summary': {
                'grade': grade,
                'completeness_score': f"{completeness:.1f}%",
                'rtm_complete': f"{complete_rtm}/{total_reqs}",
                'implemented': f"{implemented}/{total_reqs}",
                'total_issues': len(all_issues),
                'total_recommendations': len(all_recommendations)
            },
            'top_findings': {
                'strengths': self._identify_strengths(validations),
                'risks': all_issues[:3] if all_issues else ['No critical issues found'],
                'must_fix': all_issues[:1] if all_issues else []
            },
            'detailed_validations': validations,
            'recommendations': {
                'critical': all_recommendations[:2],
                'important': all_recommendations[2:5],
                'nice_to_have': all_recommendations[5:8]
            }
        }
        
        return report
    
    def _identify_strengths(self, validations: List[Dict[str, Any]]) -> List[str]:
        """Identify strengths from validation results."""
        strengths = []
        
        impl_count = sum(1 for v in validations if v['validation']['implementation_found'])
        if impl_count > len(validations) * 0.8:
            strengths.append("Strong requirement-to-code traceability")
        
        rtm_count = sum(1 for v in validations if v['validation']['rtm_complete'])
        if rtm_count > len(validations) * 0.9:
            strengths.append("Comprehensive RTM documentation")
        
        if not any(v['issues'] for v in validations):
            strengths.append("No critical issues in sampled requirements")
        
        return strengths[:3]  # Top 3 strengths

def write_audit_files(report: Dict[str, Any], output_dir: Path):
    """Write audit report to standard file structure."""
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Write executive summary
    exec_summary = f"""---
agent: {report['metadata']['agent']}
run_id: {output_dir.name}
timestamp: {report['metadata']['timestamp']}
rtm_path: {report['metadata']['rtm_path']}
method: RTM-driven sampling
sample: {{fr: {report['metadata']['sample_size']['fr']}, nfr: {report['metadata']['sample_size']['nfr']}}}
---

# Executive Summary

**Grade:** {report['summary']['grade']}  
**Completeness Score:** {report['summary']['completeness_score']}  
**RTM Complete:** {report['summary']['rtm_complete']}  
**Implementation Found:** {report['summary']['implemented']}  

## Top Strengths
{chr(10).join(f'- {s}' for s in report['top_findings']['strengths'])}

## Top Risks
{chr(10).join(f'- {r}' for r in report['top_findings']['risks'])}

## Must Fix Before Release
{chr(10).join(f'- {f}' for f in report['top_findings']['must_fix']) if report['top_findings']['must_fix'] else '- No critical fixes required'}
"""
    
    (output_dir / "executive_summary.md").write_text(exec_summary)
    
    # Write detailed findings
    detailed = ["# Detailed Findings\n"]
    for validation in report['detailed_validations']:
        req = validation['requirement']
        detailed.append(f"## {req['id']} - {req['description']}\n")
        detailed.append(f"**Tech Ref:** {req['tech_ref']}  ")
        detailed.append(f"**Arch Ref:** {req['arch_ref']}  ")
        detailed.append(f"**RTM Complete:** {'✅' if validation['validation']['rtm_complete'] else '❌'}  ")
        detailed.append(f"**Implementation Found:** {'✅' if validation['validation']['implementation_found'] else '❌'}  ")
        
        if validation['issues']:
            detailed.append("\n**Issues:**")
            for issue in validation['issues']:
                detailed.append(f"- {issue}")
        
        if validation['recommendations']:
            detailed.append("\n**Recommendations:**")
            for rec in validation['recommendations']:
                detailed.append(f"- {rec}")
        
        detailed.append("")
    
    (output_dir / "detailed_findings.md").write_text('\n'.join(detailed))
    
    # Write recommendations
    recommendations = ["# Recommendations\n"]
    
    if report['recommendations']['critical']:
        recommendations.append("## Critical (Must Fix)")
        for rec in report['recommendations']['critical']:
            recommendations.append(f"- {rec}")
        recommendations.append("")
    
    if report['recommendations']['important']:
        recommendations.append("## Important (Should Fix)")
        for rec in report['recommendations']['important']:
            recommendations.append(f"- {rec}")
        recommendations.append("")
    
    if report['recommendations']['nice_to_have']:
        recommendations.append("## Nice to Have")
        for rec in report['recommendations']['nice_to_have']:
            recommendations.append(f"- {rec}")
    
    (output_dir / "recommendations.md").write_text('\n'.join(recommendations))
    
    # Write full report as JSON artifact
    (artifacts_dir / "full_report.json").write_text(
        json.dumps(report, indent=2, default=str)
    )

def main():
    parser = argparse.ArgumentParser(description="RTM-based sampling audit")
    parser.add_argument("--rtm", default="docs/AVATAR_ENGINE_RTM.md", help="Path to RTM file")
    parser.add_argument("--docs-root", default="docs", help="Documentation root")
    parser.add_argument("--agent", default="local", help="Agent name")
    parser.add_argument("--output", default="audits", help="Output directory")
    parser.add_argument("--sample-fr", type=int, default=5, help="Number of FR to sample")
    parser.add_argument("--sample-nfr", type=int, default=5, help="Number of NFR to sample")
    
    args = parser.parse_args()
    
    # Create run directory
    timestamp = datetime.now().strftime("%Y-%m-%d")
    run_id = f"{timestamp}_run-{random.randint(1, 999):03d}"
    output_dir = Path(args.output) / args.agent / run_id
    
    # Run audit
    auditor = RTMSamplingAuditor(args.rtm, args.docs_root)
    sample = auditor.sample_requirements(args.sample_fr, args.sample_nfr)
    report = auditor.generate_audit_report(sample, args.agent)
    
    # Write results
    write_audit_files(report, output_dir)
    
    print(f"✅ Audit complete: {output_dir}")
    print(f"   Grade: {report['summary']['grade']}")
    print(f"   Issues: {report['summary']['total_issues']}")
    print(f"   Sample: {len(sample)} requirements")

if __name__ == "__main__":
    main()