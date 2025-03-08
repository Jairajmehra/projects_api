import logging

logger = logging.getLogger(__name__)

def format_residential_project(record):
    """Format a single commercial project record"""
    try:
        fields = record["fields"]
        brochure_url = ""
        cover_photo_url = ""
        certificate_url = ""
        
        if "Brochure Storage URL" in fields and fields["Brochure Storage URL"]:
            brochure_url = fields["Brochure Storage URL"]

        if "Cover Photo Storage URL" in fields and fields["Cover Photo Storage URL"]:
            cover_photo_url = fields["Cover Photo Storage URL"]

        if "Certificate Storage URL" in fields and fields["Certificate Storage URL"]:
            certificate_url = fields["Certificate Storage URL"]

        if fields.get("Photos"):
            cover_photo_url = fields.get("Photos").split(",")[0]

        return {
            "rera": fields.get("RERA Number", ""),
            "name": fields.get("Project Name", ""),
            "brochureLink": brochure_url,
            "coverPhotoLink": cover_photo_url,
            "certificateLink": certificate_url,
            "promoterName": fields.get("Promoter Name", ""),
            "mobile": fields.get("Mobile", ""),
            "projectType": fields.get("Project Type", ""),
            "startDate": fields.get("Project Start Date", ""),
            "endDate": fields.get("Project End Date", ""),
            "projectLandArea": fields.get("Land Area (Sqyrds)",""),
            "projectAddress": fields.get("Project Address",""),
            "projectStatus": fields.get("Project Status",""),
            "totalUnits": fields.get("Total Units",""),
            "totalUnitsAvailable": fields.get("Available Units",""),
            "numberOfTowers": fields.get("Total No Of Towers",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "coordinates": fields.get("coordinates",""),
            "photos": fields.get("Photos",""),
            "price": fields.get("Price",""),
            "bhk": fields.get("BHK",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "localityNames": fields.get("Name (from Locality)",""),
            "configuration": fields.get("Configuration",""),
            "airtable_id": record["id"]
        }
    except Exception as e:
        logger.error(f"Error formatting commercial project record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def format_locality(record):
    """Format a single locality record"""
    try:
        fields = record["fields"]
        return {
            "name": fields.get("Name", ""),
        }
    except Exception as e:
        logger.error(f"Error formatting locality record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def get_linked_project_photos(rera_number, residential_projects_cache):
    """Get photos from the linked project"""
    for project in residential_projects_cache:
        if project.get("rera") == rera_number[0]:
            photos = project.get("photos", "")
            return photos.split(",")
    return None

def format_residential_property(record, residential_projects_cache=None):
    """Format a single residential property record"""
    try:
        fields = record["fields"]
        photos = fields.get("Photos", "")
        linked_project_rera = fields.get("RERA Number (from residential projects)", "")
        if (not photos or photos == "" or photos == []) and linked_project_rera and residential_projects_cache:
            project_photos = get_linked_project_photos(linked_project_rera, residential_projects_cache)
            if project_photos:
                photos = project_photos[0]

        return {
            "name": fields.get("Property Name", ""),
            "price": fields.get("Price", ""),
            "transactionType": fields.get("Transaction Type", ""),
            "locality": fields.get("Name (from Localities)", ""),
            "photos": photos,
            "size": fields.get("Size in Sqfts", ""),
            "propertyType": fields.get("Property Type", ""),
            "coordinates": fields.get("Property Coordinates", ""),
            "landmark": fields.get("Landmark", ""),
            "condition": fields.get("Condition", ""),
            "date": fields.get("Date", ""),
            "bhk": fields.get("BHK", ""),
            "airtable_id": record["id"],
            "linked_project_rera": fields.get("RERA Number (from residential projects)", "")
        }
    except Exception as e:
        logger.error(f"Error formatting residential property record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None
    
def format_commercial_property(record, commercial_projects_cache=None):
    """Format a single commercial property record"""
    try:
        fields = record["fields"]
        photos = fields.get("Photos", "")
        try:
            if (not photos or photos == "" or photos == []):
                photos = ''
            else:
                photos = photos.split(",")[0]
        except Exception as e:
            logger.error(f"Error formatting commercial property record: {str(e)}")
            logger.error(f"Record that caused error: {record}")
            photos = ''
        # linked_project_rera = fields.get("RERA Number (from commercial projects)", "")
        # if (not photos or photos == "" or photos == []) and linked_project_rera and commercial_projects_cache:
        #     project_photos = get_linked_project_photos(linked_project_rera, commercial_projects_cache)
        #     if project_photos:
        #         photos = project_photos[0]

        return {
            "name": fields.get("Property Name", ""),
            "price": fields.get("Price", ""),
            "transactionType": fields.get("Transaction Type", ""),
            "locality": fields.get("Name (from Localities)", ""),
            "photos": photos,
            "size": fields.get("Size in Sqfts", ""),
            "propertyType": fields.get("Property Type", ""),
            "coordinates": fields.get("Property Coordinates", ""),
            "landmark": fields.get("Landmark", ""),
            "condition": fields.get("Condition", ""),
            "date": fields.get("Date", ""),
            "airtable_id": record["id"],
        }
    except Exception as e:
        logger.error(f"Error formatting residential property record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def format_commercial_project(record):
    """Format a single commercial project record"""
    try:
        fields = record["fields"]
        brochure_url = ""
        cover_photo_url = ""
        certificate_url = ""
        
        if "Brochure Storage URL" in fields and fields["Brochure Storage URL"]:
            brochure_url = fields["Brochure Storage URL"]

        if "Cover Photo Storage URL" in fields and fields["Cover Photo Storage URL"]:
            cover_photo_url = fields["Cover Photo Storage URL"]

        if "Certificate Storage URL" in fields and fields["Certificate Storage URL"]:
            certificate_url = fields["Certificate Storage URL"]

        return {
            "rera": fields.get("RERA Number", ""),
            "name": fields.get("Project Name", ""),
            "brochureLink": brochure_url,
            "coverPhotoLink": cover_photo_url,
            "certificateLink": certificate_url,
            "promoterName": fields.get("Promoter Name", ""),
            "email": fields.get("Email Id", ""),
            "promoterPhone": fields.get("Promoter Phone", ""),
            "promoterAddress": fields.get("Promoter Address", ""),
            "mobile": fields.get("Mobile", ""),
            "projectType": fields.get("Project Type", ""),
            "district": fields.get("District", ""),
            "approvedDate": fields.get("Approved on", ""),
            "originalEndDate": fields.get("Project Original End Date",""),
            "extendedEndDate": fields.get("Project Extended End Date",""),
            "projectLandArea": fields.get("Project Land Area (Sq Mtrs)",""),
            "averageCarpetArea": fields.get("Average Carpet Area of Units (Sq Mtrs)",""),
            "totalOpenArea": fields.get("Total Open Area (Sq Mtrs)",""),
            "totalCoveredArea": fields.get("Total Covered Area (Sq Mtrs)",""),
            "projectAddress": fields.get("Project Address",""),
            "aboutProject": fields.get("About Property",""),
            "startDate": fields.get("Project Start Date",""),
            "endDate": fields.get("Project End Date",""),
            "projectStatus": fields.get("Project Status",""),
            "type": fields.get("Type",""),
            "totalUnits": fields.get("Total Units",""),
            "totalUnitsAvailable": fields.get("Available Units",""),
            "numberOfTowers": fields.get("Total No Of Towers",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "Coordinates": fields.get("Coordinates",""),
        }
    except Exception as e:
        logger.error(f"Error formatting commercial project record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None
