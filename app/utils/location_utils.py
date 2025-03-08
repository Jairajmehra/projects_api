from app.models.schemas import ProjectCoordinates, ViewportParams

def is_point_in_viewport(coords: ProjectCoordinates, viewport: ViewportParams) -> bool:
    """Check if a point falls within the viewport"""
    return (viewport.min_lat <= coords.lat <= viewport.max_lat and 
            viewport.min_lng <= coords.lng <= viewport.max_lng)

def filter_projects_by_viewport(projects: list, viewport: ViewportParams) -> list:
    """Filter projects based on viewport boundaries"""
    filtered_projects = []
    
    for project in projects:
        try:
            # Try both coordinate field names
            coord_str = project.get("coordinates", "") or project.get("Coordinates", "")
            if not coord_str:
                continue
                
            coords = ProjectCoordinates(coord_str)
            if is_point_in_viewport(coords, viewport):
                filtered_projects.append(project)
        except ValueError:
            # Skip projects with invalid coordinates
            continue
            
    return filtered_projects
