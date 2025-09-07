import pymysql
import yaml
import os
import re
from collections import OrderedDict

def mysql_type_to_openapi_type(mysql_type):
    """Convert MySQL data types to OpenAPI data types with enhanced mapping"""
    mysql_type = mysql_type.lower()
    
    if 'int' in mysql_type:
        if 'bigint' in mysql_type:
            return {'type': 'integer', 'format': 'int64'}
        elif 'tinyint(1)' in mysql_type:
            return {'type': 'boolean'}
        else:
            return {'type': 'integer', 'format': 'int32'}
    elif 'float' in mysql_type or 'double' in mysql_type or 'decimal' in mysql_type:
        return {'type': 'number', 'format': 'double'}
    elif 'varchar' in mysql_type or 'text' in mysql_type or 'char' in mysql_type:
        return {'type': 'string'}
    elif 'datetime' in mysql_type or 'timestamp' in mysql_type:
        return {'type': 'string', 'format': 'date-time'}
    elif 'date' in mysql_type:
        return {'type': 'string', 'format': 'date'}
    elif 'time' in mysql_type:
        return {'type': 'string', 'format': 'time'}
    elif 'bool' in mysql_type:
        return {'type': 'boolean'}
    elif 'json' in mysql_type:
        return {'type': 'object'}
    elif 'enum' in mysql_type:
        return {'type': 'string'}
    else:
        return {'type': 'string'}

def is_valid_table_name(table_name):
    """Check if table name is valid"""
    return bool(re.match(r'^[a-zA-Z0-9_]+$', table_name.strip()))

def table_exists(cursor, table_name):
    """Check if table exists"""
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        return True
    except pymysql.err.ProgrammingError:
        return False

def should_generate_query_params_individual(table_name):
    """Enhanced logic for determining which tables should get query parameters"""
    table_name_lower = table_name.lower()
    
    # Core business tables that need search functionality
    high_priority_tables = [
        'users', 'tasks', 'parenttasks', 'taskassignments', 
        'assignmentactions', 'taskconflicts', 'notifications',
        'taskrecurrencerule', 'reminders', 'emergencycontacts',
        'familyaccount', 'caregivers', 'seniors', 'family'
    ]
    
    # Medium priority tables
    medium_priority_tables = [
        'categories', 'priorities', 'statuses', 'roles',
        'settings', 'preferences', 'schedules'
    ]
    
    # Skip system/lookup tables
    system_tables = [
        'categorypriority', 'conflictactions', 'conflictsuggestions',
        'log_', 'audit_', 'temp_', 'backup_'
    ]
    
    # Check if it's a system table
    if any(sys_table in table_name_lower for sys_table in system_tables):
        return False
    
    # Check if it's a high or medium priority table
    return (any(table in table_name_lower for table in high_priority_tables) or
            any(table in table_name_lower for table in medium_priority_tables))

def add_smart_query_params(columns, table_name):
    """Add intelligent query parameters based on table structure and name"""
    
    if not should_generate_query_params_individual(table_name):
        return []
    
    parameters = []
    table_name_lower = table_name.lower()
    
    # Extract column information for smart parameter generation
    column_names = [col[0].lower() for col in columns]
    
    # Add table-specific search parameters
    if 'users' in table_name_lower or 'user' in table_name_lower:
        parameters.extend([
            OrderedDict([
                ('name', 'role_id'),
                ('in', 'query'),
                ('required', False),
                ('schema', OrderedDict([
                    ('type', 'integer'),
                    ('enum', [1, 2, 3]),
                    ('description', '1=Senior, 2=Family, 3=Caregiver')
                ])),
                ('description', 'Filter by user role')
            ]),
            OrderedDict([
                ('name', 'active'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'boolean'}),
                ('description', 'Filter by active status')
            ])
        ])
        
        if any('name' in col for col in column_names):
            parameters.append(OrderedDict([
                ('name', 'name_search'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'string', 'minLength': 2}),
                ('description', 'Search by name (partial match, minimum 2 characters)')
            ]))
    
    elif 'task' in table_name_lower:
        parameters.extend([
            OrderedDict([
                ('name', 'status_id'),
                ('in', 'query'),
                ('required', False),
                ('schema', OrderedDict([
                    ('type', 'integer'),
                    ('enum', [1, 2, 3, 4]),
                    ('description', '1=Pending, 2=In Progress, 3=Completed, 4=Cancelled')
                ])),
                ('description', 'Filter by task status')
            ]),
            OrderedDict([
                ('name', 'priority_level'),
                ('in', 'query'),
                ('required', False),
                ('schema', OrderedDict([
                    ('type', 'integer'),
                    ('minimum', 1),
                    ('maximum', 5)
                ])),
                ('description', 'Filter by priority level (1=Low, 5=Critical)')
            ]),
            OrderedDict([
                ('name', 'assigned_to'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type', 'integer'}),
                ('description', 'Filter by assigned user ID')
            ])
        ])
        
        if any('due' in col for col in column_names):
            parameters.extend([
                OrderedDict([
                    ('name', 'due_date_from'),
                    ('in', 'query'),
                    ('required', False),
                    ('schema', {'type': 'string', 'format': 'date'}),
                    ('description', 'Filter tasks due from this date')
                ]),
                OrderedDict([
                    ('name', 'due_date_to'),
                    ('in', 'query'),
                    ('required', False),
                    ('schema', {'type': 'string', 'format': 'date'}),
                    ('description', 'Filter tasks due until this date')
                ])
            ])
    
    elif 'contact' in table_name_lower:
        parameters.extend([
            OrderedDict([
                ('name', 'relationship'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'string'}),
                ('description', 'Filter by relationship type')
            ]),
            OrderedDict([
                ('name', 'is_emergency'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'boolean'}),
                ('description', 'Filter emergency contacts only')
            ])
        ])
    
    elif 'notification' in table_name_lower:
        parameters.extend([
            OrderedDict([
                ('name', 'is_read'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'boolean'}),
                ('description', 'Filter by read status')
            ]),
            OrderedDict([
                ('name', 'notification_type'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'string'}),
                ('description', 'Filter by notification type')
            ])
        ])
    
    # Add date range filtering for tables with created_at/updated_at
    if any('created_at' in col for col in column_names):
        parameters.extend([
            OrderedDict([
                ('name', 'created_from'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'string', 'format': 'date-time'}),
                ('description', 'Filter records created from this date/time')
            ]),
            OrderedDict([
                ('name', 'created_to'),
                ('in', 'query'),
                ('required', False),
                ('schema', {'type': 'string', 'format': 'date-time'}),
                ('description', 'Filter records created until this date/time')
            ])
        ])
    
    # Generic search parameter for tables with text fields
    text_columns = [col[0] for col in columns if 'varchar' in col[1].lower() or 'text' in col[1].lower()]
    if text_columns and len(text_columns) > 1:
        parameters.append(OrderedDict([
            ('name', 'search'),
            ('in', 'query'),
            ('required', False),
            ('schema', {'type': 'string', 'minLength': 3}),
            ('description', f'Global search across text fields: {", ".join(text_columns[:3])}{"..." if len(text_columns) > 3 else ""}')
        ]))
    
    # Standard pagination and sorting parameters
    parameters.extend([
        OrderedDict([
            ('name', 'page'),
            ('in', 'query'),
            ('required', False),
            ('schema', OrderedDict([
                ('type', 'integer'),
                ('minimum', 1),
                ('default', 1)
            ])),
            ('description', 'Page number for pagination')
        ]),
        OrderedDict([
            ('name', 'limit'),
            ('in', 'query'),
            ('required', False),
            ('schema', OrderedDict([
                ('type', 'integer'),
                ('minimum', 1),
                ('maximum', 100),
                ('default', 20)
            ])),
            ('description', 'Number of items per page')
        ]),
        OrderedDict([
            ('name', 'sort_by'),
            ('in', 'query'),
            ('required', False),
            ('schema', OrderedDict([
                ('type', 'string'),
                ('enum', [col[0] for col in columns[:10]])  # First 10 columns as sortable options
            ])),
            ('description', 'Field to sort by')
        ]),
        OrderedDict([
            ('name', 'sort_order'),
            ('in', 'query'),
            ('required', False),
            ('schema', OrderedDict([
                ('type', 'string'),
                ('enum', ['asc', 'desc']),
                ('default', 'asc')
            ])),
            ('description', 'Sort order (ascending or descending)')
        ])
    ])
    
    return parameters

def create_enhanced_individual_table_spec(table_name, columns):
    """Create enhanced individual OpenAPI specification for a single table"""
    
    # Build schemas with enhanced field validation
    table_schema = OrderedDict([
        ('type', 'object'),
        ('properties', OrderedDict()),
        ('required', [])
    ])
    
    new_table_schema = OrderedDict([
        ('type', 'object'),
        ('properties', OrderedDict()),
        ('required', [])
    ])
    
    primary_key_column = None
    has_auto_increment = False
    
    for column in columns:
        col_name = column[0]
        col_type = column[1]
        is_nullable = column[2] == 'YES'
        col_key = column[3]
        col_default = column[4]
        col_extra = column[5] if len(column) > 5 else ''
        
        if col_key == 'PRI':
            primary_key_column = col_name
            if 'auto_increment' in col_extra.lower():
                has_auto_increment = True
        
        openapi_type = mysql_type_to_openapi_type(col_type)
        
        # Enhanced field validation and formatting
        if col_key == 'PRI':
            openapi_type['readOnly'] = True
            openapi_type['description'] = f'Primary key for {table_name}'
        elif 'email' in col_name.lower():
            openapi_type['format'] = 'email'
            openapi_type['description'] = 'Valid email address'
            openapi_type['example'] = 'user@example.com'
        elif 'phone' in col_name.lower():
            openapi_type['pattern'] = '^[+]?[1-9]?[0-9]{7,15}$'
            openapi_type['description'] = 'Phone number (7-15 digits)'
            openapi_type['example'] = '+1234567890'
        elif col_name.lower() == 'priority_level_id':
            openapi_type['minimum'] = 1
            openapi_type['maximum'] = 5
            openapi_type['description'] = 'Priority level (1=Low, 2=Medium, 3=High, 4=Urgent, 5=Critical)'
        elif col_name.lower() == 'age':
            openapi_type['minimum'] = 0
            openapi_type['maximum'] = 150
            openapi_type['description'] = 'Age in years'
        elif 'status' in col_name.lower():
            openapi_type['description'] = 'Status identifier'
        elif 'created_at' in col_name.lower():
            openapi_type['description'] = 'Record creation timestamp'
            openapi_type['readOnly'] = True
        elif 'updated_at' in col_name.lower():
            openapi_type['description'] = 'Last update timestamp'
            openapi_type['readOnly'] = True
        elif col_name.lower().endswith('_id') and col_name.lower() != primary_key_column:
            openapi_type['description'] = f'Foreign key reference to related entity'
        elif 'name' in col_name.lower():
            openapi_type['description'] = 'Name or title'
            if openapi_type['type'] == 'string':
                openapi_type['minLength'] = 1
                openapi_type['maxLength'] = 255
        elif 'description' in col_name.lower():
            openapi_type['description'] = 'Detailed description'
            if openapi_type['type'] == 'string':
                openapi_type['maxLength'] = 1000
        
        table_schema['properties'][col_name] = openapi_type.copy()
        
        if not is_nullable:
            table_schema['required'].append(col_name)
        
        # Create schema (exclude auto-increment primary keys and read-only fields)
        if not (col_key == 'PRI' and has_auto_increment) and not openapi_type.get('readOnly', False):
            create_type = openapi_type.copy()
            if 'readOnly' in create_type:
                del create_type['readOnly']
            new_table_schema['properties'][col_name] = create_type
            
            if not is_nullable and col_key != 'PRI':
                new_table_schema['required'].append(col_name)
    
    # Schema names
    schema_name = table_name.capitalize()
    new_schema_name = f"Create{schema_name[:-1] if schema_name.endswith('s') else schema_name}"
    update_schema_name = f"Update{schema_name[:-1] if schema_name.endswith('s') else schema_name}"
    resource_name = table_name[:-1] if table_name.endswith('s') else table_name
    
    # Create update schema (all fields optional)
    update_table_schema = OrderedDict([
        ('type', 'object'),
        ('properties', new_table_schema['properties'].copy()),
        ('required', [])  # No required fields for updates
    ])
    
    # Create OpenAPI specification
    openapi_spec = OrderedDict([
        ('openapi', '3.1.0'),
        ('info', OrderedDict([
            ('title', f'{schema_name} Management API'),
            ('description', f'Individual microservice API for managing {table_name} in the Seniorcare ecosystem. Provides comprehensive CRUD operations with intelligent search, filtering, and validation.'),
            ('version', '2.1.0'),
            ('contact', OrderedDict([
                ('name', f'{schema_name} API Support'),
                ('email', f'{table_name}-api@seniorcare.com'),
                ('url', f'https://docs.seniorcare.com/apis/{table_name}')
            ])),
            ('license', OrderedDict([
                ('name', 'MIT'),
                ('url', 'https://opensource.org/licenses/MIT')
            ]))
        ])),
        ('servers', [
            OrderedDict([
                ('url', f'https://api.seniorcare.com/v1/{table_name}'),
                ('description', f'Production {table_name} service')
            ]),
            OrderedDict([
                ('url', f'https://staging-api.seniorcare.com/v1/{table_name}'),
                ('description', f'Staging {table_name} service')
            ]),
            OrderedDict([
                ('url', f'http://localhost:8080/v1/{table_name}'),
                ('description', f'Local development {table_name} service')
            ])
        ]),
        ('paths', OrderedDict()),
        ('components', OrderedDict([
            ('schemas', OrderedDict([
                (schema_name, table_schema),
                (new_schema_name, new_table_schema),
                (update_schema_name, update_table_schema),
                ('PaginationMeta', OrderedDict([
                    ('type', 'object'),
                    ('properties', OrderedDict([
                        ('page', OrderedDict([
                            ('type', 'integer'),
                            ('description', 'Current page number')
                        ])),
                        ('limit', OrderedDict([
                            ('type', 'integer'),
                            ('description', 'Items per page')
                        ])),
                        ('total', OrderedDict([
                            ('type', 'integer'),
                            ('description', 'Total number of items')
                        ])),
                        ('pages', OrderedDict([
                            ('type', 'integer'),
                            ('description', 'Total number of pages')
                        ])),
                        ('has_next', OrderedDict([
                            ('type', 'boolean'),
                            ('description', 'Whether there is a next page')
                        ])),
                        ('has_prev', OrderedDict([
                            ('type', 'boolean'),
                            ('description', 'Whether there is a previous page')
                        ]))
                    ])),
                    ('required', ['page', 'limit', 'total', 'pages'])
                ]))
            ])),
            ('responses', OrderedDict([
                ('ValidationError', OrderedDict([
                    ('description', 'Validation error with detailed field-level errors'),
                    ('content', OrderedDict([
                        ('application/json', OrderedDict([
                            ('schema', OrderedDict([
                                ('type', 'object'),
                                ('properties', OrderedDict([
                                    ('error', OrderedDict([
                                        ('type', 'string'),
                                        ('example', 'Validation failed')
                                    ])),
                                    ('code', OrderedDict([
                                        ('type', 'string'),
                                        ('example', 'VALIDATION_ERROR')
                                    ])),
                                    ('details', OrderedDict([
                                        ('type', 'array'),
                                        ('items', OrderedDict([
                                            ('type', 'object'),
                                            ('properties', OrderedDict([
                                                ('field', {'type': 'string'}),
                                                ('message', {'type': 'string'}),
                                                ('code', {'type': 'string'})
                                            ]))
                                        ]))
                                    ]))
                                ])),
                                ('required', ['error', 'code'])
                            ]))
                        ]))
                    ]))
                ])),
                ('NotFound', OrderedDict([
                    ('description', 'Resource not found'),
                    ('content', OrderedDict([
                        ('application/json', OrderedDict([
                            ('schema', OrderedDict([
                                ('type', 'object'),
                                ('properties', OrderedDict([
                                    ('error', OrderedDict([
                                        ('type', 'string'),
                                        ('example', f'{resource_name.capitalize()} not found')
                                    ])),
                                    ('code', OrderedDict([
                                        ('type', 'string'),
                                        ('example', 'NOT_FOUND')
                                    ]))
                                ])),
                                ('required', ['error', 'code'])
                            ]))
                        ]))
                    ]))
                ])),
                ('Conflict', OrderedDict([
                    ('description', 'Resource conflict (duplicate, constraint violation)'),
                    ('content', OrderedDict([
                        ('application/json', OrderedDict([
                            ('schema', OrderedDict([
                                ('type', 'object'),
                                ('properties', OrderedDict([
                                    ('error', OrderedDict([
                                        ('type', 'string'),
                                        ('example', 'Resource already exists')
                                    ])),
                                    ('code', OrderedDict([
                                        ('type', 'string'),
                                        ('example', 'CONFLICT')
                                    ]))
                                ]))
                            ]))
                        ]))
                    ]))
                ]))
            ]))
        ]))
    ])
    
    # Generate smart query parameters
    query_params = add_smart_query_params(columns, table_name)
    
    # Root collection endpoint with enhanced functionality
    get_endpoint = OrderedDict([
        ('summary', f'List all {table_name}'),
        ('description', f'Retrieve a paginated list of {table_name} with advanced filtering, search, and sorting capabilities'),
        ('operationId', f'list{schema_name}'),
        ('tags', [table_name.capitalize()]),
        ('responses', OrderedDict([
            ('200', OrderedDict([
                ('description', f'Successfully retrieved list of {table_name}'),
                ('content', OrderedDict([
                    ('application/json', OrderedDict([
                        ('schema', OrderedDict([
                            ('type', 'object'),
                            ('properties', OrderedDict([
                                ('data', OrderedDict([
                                    ('type', 'array'),
                                    ('items', {'$ref': f'#/components/schemas/{schema_name}'})
                                ])),
                                ('meta', {'$ref': '#/components/schemas/PaginationMeta'})
                            ])),
                            ('required', ['data', 'meta'])
                        ]))
                    ]))
                ]))
            ])),
            ('400', {'$ref': '#/components/responses/ValidationError'})
        ]))
    ])
    
    if query_params:
        get_endpoint['parameters'] = query_params
    
    # POST endpoint with enhanced validation
    post_endpoint = OrderedDict([
        ('summary', f'Create new {resource_name}'),
        ('description', f'Create a new {resource_name} record with comprehensive validation'),
        ('operationId', f'create{schema_name[:-1] if schema_name.endswith("s") else schema_name}'),
        ('tags', [table_name.capitalize()]),
        ('requestBody', OrderedDict([
            ('required', True),
            ('content', OrderedDict([
                ('application/json', OrderedDict([
                    ('schema', {'$ref': f'#/components/schemas/{new_schema_name}'})
                ]))
            ]))
        ])),
        ('responses', OrderedDict([
            ('201', OrderedDict([
                ('description', f'{resource_name.capitalize()} created successfully'),
                ('content', OrderedDict([
                    ('application/json', OrderedDict([
                        ('schema', {'$ref': f'#/components/schemas/{schema_name}'})
                    ]))
                ]))
            ])),
            ('400', {'$ref': '#/components/responses/ValidationError'}),
            ('409', {'$ref': '#/components/responses/Conflict'})
        ]))
    ])
    
    openapi_spec['paths']['/'] = OrderedDict([
        ('get', get_endpoint),
        ('post', post_endpoint)
    ])
    
    # Individual resource endpoints with enhanced operations
    if primary_key_column:
        pk_type = 'integer' if 'int' in [col[1].lower() for col in columns if col[0] == primary_key_column][0] else 'string'
        pk_schema = OrderedDict([('type', pk_type)])
        if pk_type == 'integer':
            pk_schema['format'] = 'int64'
            pk_schema['minimum'] = 1
        
        openapi_spec['paths'][f'/{{{primary_key_column}}}'] = OrderedDict([
            ('get', OrderedDict([
                ('summary', f'Get {resource_name} by ID'),
                ('description', f'Retrieve a specific {resource_name} by its identifier'),
                ('operationId', f'get{schema_name[:-1] if schema_name.endswith("s") else schema_name}ById'),
                ('tags', [table_name.capitalize()]),
                ('parameters', [OrderedDict([
                    ('name', primary_key_column),
                    ('in', 'path'),
                    ('required', True),
                    ('schema', pk_schema),
                    ('description', f'The unique identifier of the {resource_name}')
                ])]),
                ('responses', OrderedDict([
                    ('200', OrderedDict([
                        ('description', f'{resource_name.capitalize()} found'),
                        ('content', OrderedDict([
                            ('application/json', OrderedDict([
                                ('schema', {'$ref': f'#/components/schemas/{schema_name}'})
                            ]))
                        ]))
                    ])),
                    ('404', {'$ref': '#/components/responses/NotFound'})
                ]))
            ])),
            ('put', OrderedDict([
                ('summary', f'Update {resource_name} (full replace)'),
                ('description', f'Completely replace an existing {resource_name} with new data'),
                ('operationId', f'update{schema_name[:-1] if schema_name.endswith("s") else schema_name}'),
                ('tags', [table_name.capitalize()]),
                ('parameters', [OrderedDict([
                    ('name', primary_key_column),
                    ('in', 'path'),
                    ('required', True),
                    ('schema', pk_schema),
                    ('description', f'The unique identifier of the {resource_name}')
                ])]),
                ('requestBody', OrderedDict([
                    ('required', True),
                    ('content', OrderedDict([
                        ('application/json', OrderedDict([
                            ('schema', {'$ref': f'#/components/schemas/{new_schema_name}'})
                        ]))
                    ]))
                ])),
                ('responses', OrderedDict([
                    ('200', OrderedDict([
                        ('description', f'{resource_name.capitalize()} updated successfully'),
                        ('content', OrderedDict([
                            ('application/json', OrderedDict([
                                ('schema', {'$ref': f'#/components/schemas/{schema_name}'})
                            ]))
                        ]))
                    ])),
                    ('404', {'$ref': '#/components/responses/NotFound'}),
                    ('400', {'$ref': '#/components/responses/ValidationError'})
                ]))
            ])),
            ('patch', OrderedDict([
                ('summary', f'Partially update {resource_name}'),
                ('description', f'Update specific fields of an existing {resource_name}'),
                ('operationId', f'patch{schema_name[:-1] if schema_name.endswith("s") else schema_name}'),
                ('tags', [table_name.capitalize()]),
                ('parameters', [OrderedDict([
                    ('name', primary_key_column),
                    ('in', 'path'),
                    ('required', True),
                    ('schema', pk_schema),
                    ('description', f'The unique identifier of the {resource_name}')
                ])]),
                ('requestBody', OrderedDict([
                    ('required', True),
                    ('content', OrderedDict([
                        ('application/json', OrderedDict([
                            ('schema', {'$ref': f'#/components/schemas/{update_schema_name}'})
                        ]))
                    ]))
                ])),
                ('responses', OrderedDict([
                    ('200', OrderedDict([
                        ('description', f'{resource_name.capitalize()} partially updated successfully'),
                        ('content', OrderedDict([
                            ('application/json', OrderedDict([
                                ('schema', {'$ref': f'#/components/schemas/{schema_name}'})
                            ]))
                        ]))
                    ])),
                    ('404', {'$ref': '#/components/responses/NotFound'}),
                    ('400', {'$ref': '#/components/responses/ValidationError'})
                ]))
            ])),
            ('delete', OrderedDict([
                ('summary', f'Delete {resource_name}'),
                ('description', f'Permanently delete a {resource_name} from the system'),
                ('operationId', f'delete{schema_name[:-1] if schema_name.endswith("s") else schema_name}'),
                ('tags', [table_name.capitalize()]),
                ('parameters', [OrderedDict([
                    ('name', primary_key_column),
                    ('in', 'path'),
                    ('required', True),
                    ('schema', pk_schema),
                    ('description', f'The unique identifier of the {resource_name}')
                ])]),
                ('responses', OrderedDict([
                    ('204', OrderedDict([
                        ('description', f'{resource_name.capitalize()} deleted successfully')
                    ])),
                    ('404', {'$ref': '#/components/responses/NotFound'})
                ]))
            ]))
        ])
    
    return openapi_spec

def export_enhanced_individual_openapi_specs():
    """Export enhanced individual OpenAPI specs for each table"""
    try:
        print(" Enhanced Seniorcare Individual OpenAPI Generator Started...")
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='YourDatabasePassword',
            database='YourDatabaseName',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        print("、 Connected to database successfully!")
        
        cursor.execute("SHOW TABLES")
        raw_tables = cursor.fetchall()
        
        if not raw_tables:
            print("❌ No tables found!")
            return
        
        # Filter and validate table names
        valid_tables = []
        invalid_tables = []
        
        for table_tuple in raw_tables:
            table_name = table_tuple[0].strip()
            
            if is_valid_table_name(table_name) and table_exists(cursor, table_name):
                valid_tables.append(table_name)
            else:
                invalid_tables.append(table_name)
                print(f" Skipping invalid/non-existent table: '{table_name}'")
        
        if not valid_tables:
            print("❌ No valid tables found!")
            return
        
        print(f"📋 Found {len(valid_tables)} valid tables")
        if invalid_tables:
            print(f" Skipped {len(invalid_tables)} invalid tables")
        
        # Create output directory
        os.makedirs('exports/individual_apis_enhanced', exist_ok=True)
        
        # Custom YAML representer to maintain order and style
        def represent_ordereddict(dumper, data):
            return dumper.represent_dict(data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict)
        
        generated_files = []
        searchable_apis = []
        system_apis = []
        
        for table_name in valid_tables:
            try:
                print(f"\n📋 Processing table: {table_name}")
                
                # Get column information
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                
                if not columns:
                    print(f"     Table {table_name} has no columns, skipping...")
                    continue
                
                # Create enhanced OpenAPI spec
                openapi_spec = create_enhanced_individual_table_spec(table_name, columns)
                
                # Save individual OpenAPI specification
                output_file = f'exports/individual_apis_enhanced/{table_name}_api.yaml'
                
                with open(output_file, 'w', encoding='utf-8') as file:
                    yaml.dump(openapi_spec, file, default_flow_style=False, 
                             allow_unicode=True, indent=2, width=1000, sort_keys=False)
                
                generated_files.append(output_file)
                
                # Categorize the API
                has_search_params = should_generate_query_params_individual(table_name)
                if has_search_params:
                    searchable_apis.append(table_name)
                    status_text = "Searchable API"
                else:
                    system_apis.append(table_name)
                    status_text = "System/Reference API"
                
                print(f"    Generated: {output_file}")
                print(f"   {status_icon} Type: {status_text}")
                print(f"    Columns: {len(columns)}")
                
                # Show some key features added
                features = []
                if has_search_params:
                    features.append("Smart filtering")
                if any('email' in col[0].lower() for col in columns):
                    features.append("Email validation")
                if any('phone' in col[0].lower() for col in columns):
                    features.append("Phone validation")
                if any('created_at' in col[0].lower() for col in columns):
                    features.append("Date range filtering")
                
                if features:
                    print(f"   Features: {', '.join(features)}")
                
            except Exception as table_error:
                print(f"   ❌ Error processing table {table_name}: {table_error}")
                continue
        
        connection.close()
        
        # Generate summary report
        print(f"\n Enhanced Individual API Generation Completed!")
        print(f"=" * 60)
        print(f" Generation Summary:")
        print(f"   Total APIs Generated: {len(generated_files)}")
        print(f"    Searchable APIs: {len(searchable_apis)}")
        print(f"     System/Reference APIs: {len(system_apis)}")
        
        print(f"\n Searchable APIs ({len(searchable_apis)}):")
        for api in searchable_apis:
            print(f"   - {api}")
        
        print(f"\n  System/Reference APIs ({len(system_apis)}):")
        for api in system_apis:
            print(f"   - {api}")
        
        print(f"\n Output Directory: exports/individual_apis_enhanced/")
        
    
        # Create index file with all APIs
        index_content = OrderedDict([
            ('seniorcare_individual_apis', OrderedDict([
                ('version', '2.1.0'),
                ('description', 'Enhanced individual microservice APIs for Seniorcare system'),
                ('generated_at', 'auto-generated'),
                ('apis', OrderedDict([
                    ('searchable', OrderedDict([
                        (api, f'{api}_api_v2.1.yaml') for api in searchable_apis
                    ])),
                    ('system', OrderedDict([
                        (api, f'{api}_api_v2.1.yaml') for api in system_apis
                    ]))
                ]))
            ]))
        ])
        
        with open('exports/individual_apis_enhanced/api_index.yaml', 'w', encoding='utf-8') as file:
            yaml.dump(index_content, file, default_flow_style=False, 
                     allow_unicode=True, indent=2, sort_keys=False)
        
        print(f"\n📋 API Index created: exports/individual_apis_enhanced/api_index.yaml")
        
    except Exception as e:
        print(f"❌ Error during export: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":

    export_enhanced_individual_openapi_specs()
