"""
Schema validation for extracted data using Pydantic.
"""

from typing import Dict, Any, List, Optional, Union, Type
import logging
from pydantic import BaseModel, ValidationError, Field, validator
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractedField(BaseModel):
    """Base model for a single extracted field."""
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    formatted_value: Optional[str] = None
    alternatives: List[Dict[str, Any]] = []


class ExtractionResult(BaseModel):
    """Model for complete extraction results."""
    fields: Dict[str, Any]
    metadata: Dict[str, Any]
    formatting_preserved: Dict[str, str] = {}
    confidence_scores: Dict[str, float] = {}
    alternative_matches: Dict[str, List[Dict[str, Any]]] = {}
    validation: Optional[Dict[str, Any]] = None


class ChemicalCompound(BaseModel):
    """Schema for chemical compound data."""
    name: Optional[str] = None
    formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    cas_number: Optional[str] = None
    concentration: Optional[str] = None
    temperature: Optional[str] = None
    
    @validator('cas_number')
    def validate_cas_number(cls, v):
        if v and not re.match(r'^\d{2,7}-\d{2}-\d$', v):
            raise ValueError('Invalid CAS number format')
        return v
    
    @validator('formula')
    def validate_formula(cls, v):
        if v and not re.match(r'^[A-Z][a-z]?(?:\d+|[₀-₉]+)?(?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)*$', v):
            raise ValueError('Invalid chemical formula format')
        return v


class ScientificPublication(BaseModel):
    """Schema for scientific publication data."""
    title: Optional[str] = None
    authors: List[str] = []
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = []
    
    @validator('doi')
    def validate_doi(cls, v):
        if v and not re.match(r'^10\.\d{4,}/[^\s]+$', v):
            raise ValueError('Invalid DOI format')
        return v
    
    @validator('year')
    def validate_year(cls, v):
        if v and (v < 1800 or v > datetime.now().year + 1):
            raise ValueError('Invalid publication year')
        return v


class ProductListing(BaseModel):
    """Schema for product listing data."""
    name: Optional[str] = None
    price: Optional[float] = None
    currency: str = 'USD'
    description: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    
    @validator('price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v


class ContactInfo(BaseModel):
    """Schema for contact information."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    organization: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v


class SchemaValidator:
    """Validates extracted data against predefined or custom schemas."""
    
    def __init__(self):
        self.predefined_schemas = {
            'chemical_compound': ChemicalCompound,
            'scientific_publication': ScientificPublication,
            'product_listing': ProductListing,
            'contact_info': ContactInfo,
            'extracted_field': ExtractedField,
            'extraction_result': ExtractionResult
        }
        
        self.custom_schemas = {}
    
    def validate(self, data: Dict[str, Any], schema: Union[str, Type[BaseModel], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate extracted data against a schema.
        
        Args:
            data: Data to validate
            schema: Schema to validate against (name, Pydantic model, or dict definition)
            
        Returns:
            Validation result with errors and cleaned data
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'cleaned_data': data.copy(),
            'schema_type': None
        }
        
        try:
            # Determine schema type
            if isinstance(schema, str):
                if schema in self.predefined_schemas:
                    schema_model = self.predefined_schemas[schema]
                    validation_result['schema_type'] = schema
                elif schema in self.custom_schemas:
                    schema_model = self.custom_schemas[schema]
                    validation_result['schema_type'] = schema
                else:
                    validation_result['errors'].append(f"Unknown schema: {schema}")
                    validation_result['is_valid'] = False
                    return validation_result
            elif isinstance(schema, type) and issubclass(schema, BaseModel):
                schema_model = schema
                validation_result['schema_type'] = schema.__name__
            elif isinstance(schema, dict):
                # Create dynamic schema from dictionary
                schema_model = self._create_dynamic_schema(schema)
                validation_result['schema_type'] = 'dynamic'
            else:
                validation_result['errors'].append("Invalid schema type")
                validation_result['is_valid'] = False
                return validation_result
            
            # Validate data
            validated_data = schema_model(**data)
            validation_result['cleaned_data'] = validated_data.dict()
            
        except ValidationError as e:
            validation_result['is_valid'] = False
            for error in e.errors():
                error_msg = f"Field '{'.'.join(str(loc) for loc in error['loc'])}': {error['msg']}"
                validation_result['errors'].append(error_msg)
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        # Additional custom validations
        validation_result = self._run_custom_validations(validation_result, data, schema)
        
        return validation_result
    
    def _create_dynamic_schema(self, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Create a dynamic Pydantic model from a schema dictionary."""
        
        # Convert schema dict to field definitions
        fields = {}
        validators_dict = {}
        
        for field_name, field_config in schema_dict.items():
            if isinstance(field_config, dict):
                field_type = field_config.get('type', str)
                field_required = field_config.get('required', False)
                field_default = field_config.get('default', None)
                
                # Convert type strings to actual types
                if field_type == 'str':
                    field_type = str
                elif field_type == 'int':
                    field_type = int
                elif field_type == 'float':
                    field_type = float
                elif field_type == 'bool':
                    field_type = bool
                elif field_type == 'list':
                    field_type = List[str]  # Default to list of strings
                
                # Create field definition
                if field_required:
                    fields[field_name] = (field_type, ...)
                else:
                    fields[field_name] = (Optional[field_type], field_default)
                
                # Add validators if specified
                if 'pattern' in field_config:
                    pattern = field_config['pattern']
                    validator_name = f'validate_{field_name}'
                    
                    def make_validator(regex_pattern):
                        def validate_field(cls, v):
                            if v and not re.match(regex_pattern, str(v)):
                                raise ValueError(f'Value does not match pattern: {regex_pattern}')
                            return v
                        return validate_field
                    
                    validators_dict[validator_name] = validator(field_name)(make_validator(pattern))
            
            else:
                # Simple type specification
                fields[field_name] = (Optional[type(field_config)], None)
        
        # Create dynamic model class
        dynamic_model = type('DynamicSchema', (BaseModel,), {**fields, **validators_dict})
        
        return dynamic_model
    
    def _run_custom_validations(self, validation_result: Dict[str, Any], data: Dict[str, Any], schema: Any) -> Dict[str, Any]:
        """Run additional custom validations."""
        
        # Check for data completeness
        non_null_fields = sum(1 for v in data.values() if v is not None)
        total_fields = len(data)
        
        if total_fields > 0:
            completeness = non_null_fields / total_fields
            if completeness < 0.5:
                validation_result['warnings'].append(f"Low data completeness: {completeness:.1%}")
        
        # Check for consistency in chemical formulas
        if 'formula' in data and 'name' in data:
            formula = data['formula']
            name = data['name']
            
            if formula and name:
                # Basic consistency check for common compounds
                common_formulas = {
                    'water': ['H2O', 'H₂O'],
                    'carbon dioxide': ['CO2', 'CO₂'],
                    'sulfuric acid': ['H2SO4', 'H₂SO₄'],
                    'sodium chloride': ['NaCl'],
                    'methane': ['CH4', 'CH₄']
                }
                
                name_lower = name.lower()
                for compound_name, formulas in common_formulas.items():
                    if compound_name in name_lower and formula not in formulas:
                        validation_result['warnings'].append(
                            f"Formula '{formula}' may not match compound name '{name}'"
                        )
        
        # Check for reasonable price ranges
        if 'price' in data:
            price = data['price']
            if isinstance(price, (int, float)):
                if price > 1000000:
                    validation_result['warnings'].append("Price seems unusually high")
                elif price < 0.01:
                    validation_result['warnings'].append("Price seems unusually low")
        
        # Check email format more strictly
        if 'email' in data and data['email']:
            email = data['email']
            # Check for common disposable email domains
            disposable_domains = ['10minutemail', 'temp-mail', 'guerrillamail', 'mailinator']
            for domain in disposable_domains:
                if domain in email.lower():
                    validation_result['warnings'].append("Email appears to be from a disposable service")
                    break
        
        return validation_result
    
    def add_custom_schema(self, name: str, schema_model: Type[BaseModel]) -> None:
        """Add a custom schema for validation."""
        self.custom_schemas[name] = schema_model
        logger.info(f"Added custom schema: {name}")
    
    def validate_extraction_result(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete extraction result."""
        return self.validate(extraction_result, 'extraction_result')
    
    def get_schema_info(self, schema_name: str) -> Dict[str, Any]:
        """Get information about a schema."""
        if schema_name in self.predefined_schemas:
            schema_model = self.predefined_schemas[schema_name]
        elif schema_name in self.custom_schemas:
            schema_model = self.custom_schemas[schema_name]
        else:
            return {'error': f'Schema {schema_name} not found'}
        
        # Extract field information
        fields_info = {}
        for field_name, field_info in schema_model.__fields__.items():
            fields_info[field_name] = {
                'type': str(field_info.type_),
                'required': field_info.required,
                'default': field_info.default if field_info.default is not ... else None
            }
        
        return {
            'name': schema_name,
            'fields': fields_info,
            'description': schema_model.__doc__ or ''
        }
    
    def list_available_schemas(self) -> List[str]:
        """List all available schemas."""
        return list(self.predefined_schemas.keys()) + list(self.custom_schemas.keys())
    
    def create_schema_from_sample(self, sample_data: Dict[str, Any], schema_name: str) -> Type[BaseModel]:
        """Create a schema automatically from sample data."""
        
        fields = {}
        
        for field_name, value in sample_data.items():
            if isinstance(value, str):
                field_type = str
            elif isinstance(value, int):
                field_type = int
            elif isinstance(value, float):
                field_type = float
            elif isinstance(value, bool):
                field_type = bool
            elif isinstance(value, list):
                field_type = List[str]  # Assume list of strings
            else:
                field_type = str  # Default to string
            
            # Make all fields optional with None default
            fields[field_name] = (Optional[field_type], None)
        
        # Create the schema class
        schema_class = type(schema_name, (BaseModel,), fields)
        
        # Add to custom schemas
        self.add_custom_schema(schema_name, schema_class)
        
        return schema_class
    
    def suggest_improvements(self, validation_result: Dict[str, Any]) -> List[str]:
        """Suggest improvements based on validation results."""
        suggestions = []
        
        if not validation_result['is_valid']:
            suggestions.append("Fix validation errors to improve data quality")
        
        if validation_result['warnings']:
            suggestions.append("Review warnings to ensure data accuracy")
        
        # Analyze the cleaned data for patterns
        cleaned_data = validation_result.get('cleaned_data', {})
        
        # Check for missing data
        missing_fields = [k for k, v in cleaned_data.items() if v is None or v == '']
        if missing_fields:
            suggestions.append(f"Consider extracting values for missing fields: {', '.join(missing_fields)}")
        
        # Check for low confidence scores if available
        if 'confidence_scores' in cleaned_data:
            low_confidence = [k for k, v in cleaned_data['confidence_scores'].items() if v < 0.7]
            if low_confidence:
                suggestions.append(f"Improve extraction patterns for low-confidence fields: {', '.join(low_confidence)}")
        
        return suggestions