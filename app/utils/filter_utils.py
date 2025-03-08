import logging
from typing import Union

logger = logging.getLogger(__name__)

def filter_residential_properties(properties: list, 
    price_min: float = None, 
    price_max: float = None, 
    bhk: Union[str, list] = None,
    transaction_type: str = None,
    propertyType: Union[str, list] = None,
    locality: Union[str, list] = None
) -> list:
    """
    Filters the list of properties based on various criteria.
    
    Sample property structure:
    {
        'name': 'Kalhaar Blues And Greens',
        'price': 150000,
        'transactionType': 'rent',
        'locality': ['Sanand'],  # Note: locality is a list
        'property_type': 'Bungalow/Villa',
        'bhk': '4 BHK',
        ...
    }
    """
    # Convert single values to lists for consistent handling
    # Convert bhk parameter to a list of lowercase strings
    if bhk:
        if isinstance(bhk, str):
            bhk_values = [bhk.lower()]
        else:  # it's already a list
            bhk_values = [b.lower() for b in bhk]
    else:
        bhk_values = None
    propertyTypes = [propertyType] if isinstance(propertyType, str) else propertyType if propertyType else None
    localities = [locality] if isinstance(locality, str) else locality if locality else None

    if localities:
        localities = [loc.strip().lower() for loc in localities]

    if propertyTypes:
        propertyTypes = [prop_type.strip().lower() for prop_type in propertyTypes]

    filtered = []
    for prop in properties:
        try:
            # Price handling
            prop_price = prop.get("price")
            if isinstance(prop_price, str):
                try:
                    prop_price = float(prop_price.replace(',', '').replace('₹', '').strip())
                except (ValueError, TypeError):
                    prop_price = None

            # Apply filters only if they are provided
            # Price filter
            if price_min is not None and (prop_price is None or prop_price < price_min):
                continue
            if price_max is not None and (prop_price is None or prop_price > price_max):
                continue

            # BHK filter (exact match including "BHK")
            if bhk_values:
                prop_bhk = prop.get("bhk", "").lower()
                if not any(bhk_val in prop_bhk for bhk_val in bhk_values):
                    continue

            # Transaction type filter (exact match)
            if transaction_type and prop.get("transactionType") != transaction_type:
                continue

            # Property type filter (exact match)
            if propertyTypes:
                prop_type = prop.get("propertyType", "").lower()
                # Skip this property if its type doesn't match any requested types
                if prop_type not in propertyTypes:
                    continue

            # Locality filter (check if any requested locality is in the property's locality list)
            if localities:
                  # Get the property locality and ensure it's a list
                prop_locality = prop.get("locality", "")
                # If it's a string, convert it to a list
                if isinstance(prop_locality, str):
                    prop_localities = [prop_locality.lower()]  # Convert string to list with lowercase
                else:
                    prop_localities = [loc.lower() for loc in prop_locality]  # Assume it's a list

                if not any(loc in prop_localities for loc in localities):
                    continue

            filtered.append(prop)

        except Exception as e:
            logger.error(f"Error filtering property: {str(e)}")
            logger.error(f"Problematic property: {prop}")
            continue

    return filtered


def filter_commercial_properties(properties: list, 
    price_min: float = None, 
    price_max: float = None,
    transaction_type: str = None,
    propertyType: Union[str, list] = None,
    locality: Union[str, list] = None
) -> list:
    """
    Filters the list of properties based on various criteria.
    
    Sample property structure:
    {
        'name': 'West Gate',
        'price': 150000,
        'transactionType': 'rent',
        'locality': ['Sanand'],  # Note: locality is a list
        'property_type': 'Office',
        ...
    }
    """
    # Convert single values to lists for consistent handling
    propertyTypes = [propertyType] if isinstance(propertyType, str) else propertyType if propertyType else None
    localities = [locality] if isinstance(locality, str) else locality if locality else None

    if localities:
        localities = [loc.strip().lower() for loc in localities]

    if propertyTypes:
        propertyTypes = [prop_type.strip().lower() for prop_type in propertyTypes]

    filtered = []
    for prop in properties:
        try:
            # Price handling
            prop_price = prop.get("price")
            if isinstance(prop_price, str):
                try:
                    prop_price = float(prop_price.replace(',', '').replace('₹', '').strip())
                except (ValueError, TypeError):
                    prop_price = None

            # Apply filters only if they are provided
            # Price filter
            if price_min is not None and (prop_price is None or prop_price < price_min):
                continue
            if price_max is not None and (prop_price is None or prop_price > price_max):
                continue

            # Transaction type filter (exact match)
            if transaction_type and prop.get("transactionType") != transaction_type:
                continue

            # Property type filter (exact match)
            if propertyTypes:
                prop_type = prop.get("propertyType", "").lower()
                # Skip this property if its type doesn't match any requested types
                if prop_type not in propertyTypes:
                    continue

            # Locality filter (check if any requested locality is in the property's locality list)
            if localities:
                  # Get the property locality and ensure it's a list
                prop_locality = prop.get("locality", "")
                # If it's a string, convert it to a list
                if isinstance(prop_locality, str):
                    prop_localities = [prop_locality.lower()]  # Convert string to list with lowercase
                else:
                    prop_localities = [loc.lower() for loc in prop_locality]  # Assume it's a list

                if not any(loc in prop_localities for loc in localities):
                    continue

            filtered.append(prop)

        except Exception as e:
            logger.error(f"Error filtering property: {str(e)}")
            logger.error(f"Problematic property: {prop}")
            continue

    return filtered
