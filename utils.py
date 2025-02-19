from fuzzywuzzy import fuzz
import re


def match_project_names_to_properties(project_name: str, property_name: str, threshold: int = 95) -> bool:
    """
    Match project names to properties based on similarity.
    
    Args:
        project_name: Name of the project to match
        property_name: Name of the property to compare against
        threshold: Minimum similarity score (default: 90)
    
    Returns:
        bool: True if names match above threshold, False otherwise
    """
    # Normalize both strings: lowercase and remove special characters
    normalized_project = re.sub(r'[^a-z0-9\s]', ' ', project_name.lower()).strip()
    normalized_property = re.sub(r'[^a-z0-9\s]', ' ', property_name.lower()).strip()
    
    # Calculate similarity score
    score = fuzz.token_set_ratio(normalized_project, normalized_property)
    
    # Return True if score meets threshold
    return score >= threshold