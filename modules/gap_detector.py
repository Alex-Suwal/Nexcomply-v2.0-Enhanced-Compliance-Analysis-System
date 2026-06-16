"""
Gap detection module for Nexcomply application
Identifies compliance gaps by comparing embeddings
"""

from modules.embeddings import get_embedding_generator, SimilarityCalculator
import pandas as pd


class GapDetector:
    """Class to handle gap detection operations"""
    
    def __init__(self, thresholds=None):
        """
        Initialize gap detector
        
        Args:
            thresholds: Dictionary of severity thresholds
        """
        if thresholds is None:
            self.thresholds = {
                'critical': 0.3,
                'high': 0.5,
                'medium': 0.7,
                'low': 0.85
            }
        else:
            self.thresholds = thresholds
        
        self.embedding_generator = get_embedding_generator()
        self.similarity_calculator = SimilarityCalculator()
    
    def determine_gap_severity(self, similarity_score):
        """
        Determine gap severity based on similarity score
        
        Args:
            similarity_score: Cosine similarity score (0-1)
            
        Returns:
            str: Severity level (Critical, High, Medium, Low, None)
        """
        if similarity_score < self.thresholds['critical']:
            return "Critical"
        elif similarity_score < self.thresholds['high']:
            return "High"
        elif similarity_score < self.thresholds['medium']:
            return "Medium"
        elif similarity_score < self.thresholds['low']:
            return "Low"
        else:
            return "None"
    
    def detect_gap(self, requirement_text, response_text, threshold=0.7):
        """
        Detect gap between requirement and response
        
        Args:
            requirement_text: Compliance requirement text
            response_text: Internal response/policy text
            threshold: Similarity threshold for gap detection
            
        Returns:
            dict: Gap detection result
        """
        # Generate embeddings
        req_embedding = self.embedding_generator.generate_embedding(requirement_text)
        res_embedding = self.embedding_generator.generate_embedding(response_text)
        
        # Calculate similarity
        similarity_score = self.similarity_calculator.calculate_cosine_similarity(
            req_embedding, res_embedding
        )
        
        # Determine severity
        severity = self.determine_gap_severity(similarity_score)
        
        # Determine if gap exists
        gap_exists = similarity_score < threshold
        
        # Generate description
        if gap_exists:
            description = f"Gap detected: Internal response does not adequately meet the compliance requirement. Similarity score: {similarity_score:.2f}"
        else:
            description = f"No significant gap: Internal response meets the compliance requirement. Similarity score: {similarity_score:.2f}"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(similarity_score, severity)
        
        return {
            'similarity_score': similarity_score,
            'gap_exists': gap_exists,
            'severity': severity,
            'description': description,
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self, similarity_score, severity):
        """
        Generate recommendations based on gap analysis
        
        Args:
            similarity_score: Similarity score
            severity: Gap severity level
            
        Returns:
            str: Recommendations text
        """
        if severity == "Critical":
            return (
                "CRITICAL ACTION REQUIRED: Immediate attention needed to address this significant compliance gap. "
                "Consider: 1) Developing new policies, 2) Implementing controls, 3) Training staff, "
                "4) Consulting with compliance experts."
            )
        elif severity == "High":
            return (
                "HIGH PRIORITY: Address this gap within the next review cycle. "
                "Consider: 1) Updating existing policies, 2) Enhancing controls, "
                "3) Documenting procedures more thoroughly."
            )
        elif severity == "Medium":
            return (
                "MODERATE ACTION NEEDED: Review and enhance alignment. "
                "Consider: 1) Clarifying policy language, 2) Adding specific controls, "
                "3) Improving documentation."
            )
        elif severity == "Low":
            return (
                "LOW PRIORITY: Minor improvements recommended. "
                "Consider: 1) Fine-tuning policy details, 2) Enhancing documentation, "
                "3) Regular monitoring."
            )
        else:
            return (
                "COMPLIANT: Continue monitoring and maintaining current controls. "
                "Consider periodic reviews to ensure continued compliance."
            )
    
    def batch_detect_gaps(self, requirements, responses, framework_name=None):
        """
        Detect gaps for multiple requirement-response pairs
        
        Args:
            requirements: List or dict of requirement texts
            responses: List or dict of response texts
            framework_name: Optional framework name for context
            
        Returns:
            list: List of gap detection results
        """
        results = []
        
        if isinstance(requirements, dict) and isinstance(responses, dict):
            for req_key, req_text in requirements.items():
                for res_key, res_text in responses.items():
                    if isinstance(req_text, str) and isinstance(res_text, str):
                        gap_result = self.detect_gap(req_text, res_text)
                        gap_result['requirement'] = req_key
                        gap_result['response'] = res_key
                        if framework_name:
                            gap_result['framework'] = framework_name
                        results.append(gap_result)
        elif isinstance(requirements, list) and isinstance(responses, list):
            for i, (req_text, res_text) in enumerate(zip(requirements, responses)):
                if isinstance(req_text, str) and isinstance(res_text, str):
                    gap_result = self.detect_gap(req_text, res_text)
                    gap_result['index'] = i
                    if framework_name:
                        gap_result['framework'] = framework_name
                    results.append(gap_result)
        
        return results
    
    def analyze_framework_vs_policies(self, framework_requirements, policy_texts):
        """
        Analyze gaps between framework requirements and internal policies
        
        Args:
            framework_requirements: List of framework requirement texts
            policy_texts: Dictionary of policy texts
            
        Returns:
            pd.DataFrame: Gap analysis results
        """
        results = []
        
        for req_idx, requirement in enumerate(framework_requirements):
            if not isinstance(requirement, str) or len(requirement) < 10:
                continue
            
            req_embedding = self.embedding_generator.generate_embedding(requirement)
            
            # Find best matching policy
            best_match = None
            best_score = 0.0
            
            for policy_name, policy_text in policy_texts.items():
                if isinstance(policy_text, str) and len(policy_text) > 10:
                    policy_embedding = self.embedding_generator.generate_embedding(policy_text)
                    score = self.similarity_calculator.calculate_cosine_similarity(
                        req_embedding, policy_embedding
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_match = policy_name
            
            severity = self.determine_gap_severity(best_score)
            
            results.append({
                'requirement_index': req_idx,
                'requirement': requirement[:100] + '...' if len(requirement) > 100 else requirement,
                'best_matching_policy': best_match,
                'similarity_score': best_score,
                'gap_severity': severity,
                'gap_exists': best_score < 0.7
            })
        
        return pd.DataFrame(results)
    
    def generate_gap_summary(self, gap_results):
        """
        Generate summary statistics for gap analysis
        
        Args:
            gap_results: List or DataFrame of gap results
            
        Returns:
            dict: Summary statistics
        """
        if isinstance(gap_results, list):
            df = pd.DataFrame(gap_results)
        else:
            df = gap_results
        
        if df.empty:
            return {
                'total_gaps': 0,
                'critical_gaps': 0,
                'high_gaps': 0,
                'medium_gaps': 0,
                'low_gaps': 0,
                'no_gaps': 0,
                'average_similarity': 0.0,
                'compliance_percentage': 100.0
            }
        
        summary = {
            'total_gaps': len(df),
            'critical_gaps': len(df[df['gap_severity'] == 'Critical']) if 'gap_severity' in df.columns else 0,
            'high_gaps': len(df[df['gap_severity'] == 'High']) if 'gap_severity' in df.columns else 0,
            'medium_gaps': len(df[df['gap_severity'] == 'Medium']) if 'gap_severity' in df.columns else 0,
            'low_gaps': len(df[df['gap_severity'] == 'Low']) if 'gap_severity' in df.columns else 0,
            'no_gaps': len(df[df['gap_severity'] == 'None']) if 'gap_severity' in df.columns else 0,
            'average_similarity': df['similarity_score'].mean() if 'similarity_score' in df.columns else 0.0,
        }
        
        # Calculate compliance percentage
        total = len(df)
        compliant = summary['no_gaps'] + summary['low_gaps']
        summary['compliance_percentage'] = (compliant / total * 100) if total > 0 else 100.0
        
        return summary


def detect_compliance_gaps(framework_text, policy_text, threshold=0.7):
    """
    Convenience function to detect gaps
    
    Args:
        framework_text: Framework requirement text
        policy_text: Internal policy text
        threshold: Similarity threshold
        
    Returns:
        dict: Gap detection result
    """
    detector = GapDetector()
    return detector.detect_gap(framework_text, policy_text, threshold)
