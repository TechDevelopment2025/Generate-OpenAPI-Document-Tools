import pymysql
import yaml
import os
import re
from collections import OrderedDict

def mysql_type_to_openapi_type(mysql_type):
    """Convert MySQL data types to OpenAPI data types"""
    mysql_type = mysql_type.lower()
    
    if 'int' in mysql_type:
        if 'bigint' in mysql_type:
            return {'type': 'integer', 'format': 'int64'}
        else:
            return {'type': 'integer', 'format': 'int32'}
    elif 'float' in mysql_type or 'double' in mysql_type or 'decimal' in mysql_type:
        return {'type': 'number', 'format': 'double'}
    elif 'varchar' in mysql_type or 'text' in mysql_type or 'char' in mysql_type:
        return {'type': 'string'}
    elif 'email' in mysql_type.lower() or 'mail' in mysql_type.lower():
        return {'type': 'string', 'format': 'email'}
    elif 'datetime' in mysql_type or 'timestamp' in mysql_type:
        return {'type': 'string', 'format': 'date-time'}
    elif 'date' in mysql_type:
        return {'type': 'string', 'format': 'date'}
    elif 'bool' in mysql_type or 'tinyint(1)' in mysql_type:
        return {'type': 'boolean'}
    elif 'json' in mysql_type:
        return {'type': 'object'}
    else:
        return {'type': 'string'}

def is_valid_table_name(table_name):
    """Check if table name is valid (no spaces, special characters, etc.)"""
    # Allow letters, numbers, underscores
    return bool(re.match(r'^[a-zA-Z0-9_]+$', table_name.strip()))

def sanitize_table_name(table_name):
    """Clean up table name by removing invalid characters"""
    return re.sub(r'[^a-zA-Z0-9_]', '', table_name.strip())

def table_exists(cursor, table_name):
    """Check if a table actually exists in the database"""
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        return True
    except pymysql.err.ProgrammingError:
        return False

def export_mysql_to_openapi_yaml():
    try:
        print("Connecting to MySQL database...")
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='YourDatabasePassword',
            database='YourDatabaseName',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        print("Connected successfully!")
        
        # Get all table names
        cursor.execute("SHOW TABLES")
        raw_tables = cursor.fetchall()
        
        if not raw_tables:
            print("No tables found in the database!")
            return
        
        # Filter and validate table names
        valid_tables = []
        invalid_tables = []
        
        for table_tuple in raw_tables:
            table_name = table_tuple[0].strip()
            
            # Check if table name is valid and table exists
            if is_valid_table_name(table_name) and table_exists(cursor, table_name):
                valid_tables.append(table_name)
            else:
                invalid_tables.append(table_name)
                print(f"⚠️  Skipping invalid/non-existent table: '{table_name}'")
        
        if not valid_tables:
            print("No valid tables found!")
            return
            
        print(f"Found {len(valid_tables)} valid tables: {valid_tables}")
        if invalid_tables:
            print(f"Skipped {len(invalid_tables)} invalid tables: {invalid_tables}")
        
        # Create output directory
        os.makedirs('openapi_specs', exist_ok=True)
        
        # Create main OpenAPI specification using OrderedDict for proper order
        openapi_spec = OrderedDict([
            ('openapi', '3.1.0'),
            ('info', OrderedDict([
                ('title', 'Seniorcare Management API'),
                ('description', 'A comprehensive API for managing Seniorcare resources.'),
                ('version', '1.0.0')
            ])),
            ('servers', [
                OrderedDict([
                    ('url', 'https://api.seniorcare.com/v1'),
                    ('description', 'Production server')
                ]),
                OrderedDict([
                    ('url', 'http://localhost:8080/v1'),
                    ('description', 'Local development server')
                ])
            ]),
            ('paths', OrderedDict()),
            ('components', OrderedDict([
                ('schemas', OrderedDict())
            ]))
        ])
        
        processed_tables = []
        
        for table_name in valid_tables:
            try:
                print(f"\n📋 Processing table: {table_name}")
                
                # Get column information with backticks for safety
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                
                if not columns:
                    print(f"   ⚠️  Table {table_name} has no columns, skipping...")
                    continue
                
                # Build main schema for this table
                table_schema = OrderedDict([
                    ('type', 'object'),
                    ('properties', OrderedDict()),
                    ('required', [])
                ])
                
                # Build "New" schema (for POST requests - without auto-increment ID)
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
                    
                    # Track primary key and auto increment
                    if col_key == 'PRI':
                        primary_key_column = col_name
                        if 'auto_increment' in col_extra.lower():
                            has_auto_increment = True
                    
                    # Convert MySQL type to OpenAPI type
                    openapi_type = mysql_type_to_openapi_type(col_type)
                    
                    # Add special properties for primary key
                    if col_key == 'PRI':
                        openapi_type['readOnly'] = True
                    
                    # Add description based on column name patterns
                    if 'email' in col_name.lower():
                        openapi_type['description'] = 'Email address'
                    elif 'phone' in col_name.lower():
                        openapi_type['description'] = 'Phone number'
                    elif 'date' in col_name.lower():
                        openapi_type['description'] = 'Date value'
                    elif col_name.lower().endswith('_id'):
                        openapi_type['description'] = f'Foreign key reference'
                    
                    # Add to main schema
                    table_schema['properties'][col_name] = openapi_type.copy()
                    
                    # Add to required if not nullable
                    if not is_nullable:
                        table_schema['required'].append(col_name)
                    
                    # Add to "New" schema (exclude auto-increment primary keys)
                    if not (col_key == 'PRI' and has_auto_increment):
                        new_table_schema['properties'][col_name] = openapi_type.copy()
                        if 'readOnly' in new_table_schema['properties'][col_name]:
                            del new_table_schema['properties'][col_name]['readOnly']
                        
                        if not is_nullable and col_key != 'PRI':
                            new_table_schema['required'].append(col_name)
                
                # Generate schema names
                schema_name = table_name.capitalize()
                new_schema_name = f"New{schema_name[:-1] if schema_name.endswith('s') else schema_name}"
                
                # Add schemas to components
                openapi_spec['components']['schemas'][schema_name] = table_schema
                openapi_spec['components']['schemas'][new_schema_name] = new_table_schema
                
                # Determine resource name (singular)
                resource_name = table_name[:-1] if table_name.endswith('s') else table_name
                
                # Add collection endpoints
                openapi_spec['paths'][f'/{table_name}'] = OrderedDict([
                    ('get', OrderedDict([
                        ('summary', f'Get all {table_name}'),
                        ('description', f'Retrieves a list of all {table_name}.'),
                        ('parameters', [
                            OrderedDict([
                                ('in', 'query'),
                                ('name', 'limit'),
                                ('schema', {'type': 'integer', 'minimum': 1, 'maximum': 1000, 'default': 100}),
                                ('description', 'Maximum number of results to return')
                            ]),
                            OrderedDict([
                                ('in', 'query'),
                                ('name', 'offset'),
                                ('schema', {'type': 'integer', 'minimum': 0, 'default': 0}),
                                ('description', 'Number of results to skip')
                            ])
                        ]),
                        ('responses', OrderedDict([
                            ('200', OrderedDict([
                                ('description', f'A list of {table_name}.'),
                                ('content', OrderedDict([
                                    ('application/json', OrderedDict([
                                        ('schema', OrderedDict([
                                            ('type', 'object'),
                                            ('properties', OrderedDict([
                                                ('data', OrderedDict([
                                                    ('type', 'array'),
                                                    ('items', OrderedDict([
                                                        ('$ref', f'#/components/schemas/{schema_name}')
                                                    ]))
                                                ])),
                                                ('total', OrderedDict([
                                                    ('type', 'integer'),
                                                    ('description', 'Total number of records')
                                                ])),
                                                ('limit', OrderedDict([
                                                    ('type', 'integer'),
                                                    ('description', 'Applied limit')
                                                ])),
                                                ('offset', OrderedDict([
                                                    ('type', 'integer'),
                                                    ('description', 'Applied offset')
                                                ]))
                                            ]))
                                        ]))
                                    ]))
                                ]))
                            ])),
                            ('400', OrderedDict([
                                ('description', 'Invalid query parameters.')
                            ]))
                        ]))
                    ])),
                    ('post', OrderedDict([
                        ('summary', f'Create a new {resource_name}'),
                        ('description', f'Adds a new {resource_name} to the system.'),
                        ('requestBody', OrderedDict([
                            ('required', True),
                            ('content', OrderedDict([
                                ('application/json', OrderedDict([
                                    ('schema', OrderedDict([
                                        ('$ref', f'#/components/schemas/{new_schema_name}')
                                    ]))
                                ]))
                            ]))
                        ])),
                        ('responses', OrderedDict([
                            ('201', OrderedDict([
                                ('description', f'{resource_name.capitalize()} created successfully.'),
                                ('content', OrderedDict([
                                    ('application/json', OrderedDict([
                                        ('schema', OrderedDict([
                                            ('$ref', f'#/components/schemas/{schema_name}')
                                        ]))
                                    ]))
                                ]))
                            ])),
                            ('400', OrderedDict([
                                ('description', 'Invalid input data.')
                            ])),
                            ('409', OrderedDict([
                                ('description', 'Resource already exists.')
                            ]))
                        ]))
                    ]))
                ])
                
                # Add individual resource endpoints if there's a primary key
                if primary_key_column:
                    pk_type = 'integer' if 'int' in [col[1].lower() for col in columns if col[0] == primary_key_column][0] else 'string'
                    pk_format = 'int64' if pk_type == 'integer' else None
                    
                    pk_schema = OrderedDict([('type', pk_type)])
                    if pk_format:
                        pk_schema['format'] = pk_format
                    
                    openapi_spec['paths'][f'/{table_name}/{{{primary_key_column}}}'] = OrderedDict([
                        ('get', OrderedDict([
                            ('summary', f'Get {resource_name} by {primary_key_column}'),
                            ('description', f'Retrieves a single {resource_name} by their {primary_key_column}.'),
                            ('parameters', [
                                OrderedDict([
                                    ('in', 'path'),
                                    ('name', primary_key_column),
                                    ('required', True),
                                    ('schema', pk_schema),
                                    ('description', f'The {primary_key_column} of the {resource_name} to retrieve.')
                                ])
                            ]),
                            ('responses', OrderedDict([
                                ('200', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} found.'),
                                    ('content', OrderedDict([
                                        ('application/json', OrderedDict([
                                            ('schema', OrderedDict([
                                                ('$ref', f'#/components/schemas/{schema_name}')
                                            ]))
                                        ]))
                                    ]))
                                ])),
                                ('404', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} not found.')
                                ]))
                            ]))
                        ])),
                        ('put', OrderedDict([
                            ('summary', f'Update {resource_name} by {primary_key_column}'),
                            ('description', f'Updates an existing {resource_name}.'),
                            ('parameters', [
                                OrderedDict([
                                    ('in', 'path'),
                                    ('name', primary_key_column),
                                    ('required', True),
                                    ('schema', pk_schema),
                                    ('description', f'The {primary_key_column} of the {resource_name} to update.')
                                ])
                            ]),
                            ('requestBody', OrderedDict([
                                ('required', True),
                                ('content', OrderedDict([
                                    ('application/json', OrderedDict([
                                        ('schema', OrderedDict([
                                            ('$ref', f'#/components/schemas/{new_schema_name}')
                                        ]))
                                    ]))
                                ]))
                            ])),
                            ('responses', OrderedDict([
                                ('200', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} updated successfully.'),
                                    ('content', OrderedDict([
                                        ('application/json', OrderedDict([
                                            ('schema', OrderedDict([
                                                ('$ref', f'#/components/schemas/{schema_name}')
                                            ]))
                                        ]))
                                    ]))
                                ])),
                                ('400', OrderedDict([
                                    ('description', 'Invalid input data.')
                                ])),
                                ('404', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} not found.')
                                ]))
                            ]))
                        ])),
                        ('delete', OrderedDict([
                            ('summary', f'Delete {resource_name} by {primary_key_column}'),
                            ('description', f'Deletes a {resource_name} from the system.'),
                            ('parameters', [
                                OrderedDict([
                                    ('in', 'path'),
                                    ('name', primary_key_column),
                                    ('required', True),
                                    ('schema', pk_schema),
                                    ('description', f'The {primary_key_column} of the {resource_name} to delete.')
                                ])
                            ]),
                            ('responses', OrderedDict([
                                ('204', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} deleted successfully.')
                                ])),
                                ('404', OrderedDict([
                                    ('description', f'{resource_name.capitalize()} not found.')
                                ]))
                            ]))
                        ]))
                    ])
                
                processed_tables.append(table_name)
                print(f"   ✅ Generated OpenAPI spec for {table_name} with {len(columns)} columns")
                
            except Exception as table_error:
                print(f"   ❌ Error processing table {table_name}: {table_error}")
                continue
        
        if not processed_tables:
            print("No tables were successfully processed!")
            return
        
        # Add error response schemas
        openapi_spec['components']['schemas']['Error'] = OrderedDict([
            ('type', 'object'),
            ('properties', OrderedDict([
                ('error', OrderedDict([
                    ('type', 'string'),
                    ('description', 'Error message')
                ])),
                ('code', OrderedDict([
                    ('type', 'integer'),
                    ('description', 'Error code')
                ])),
                ('details', OrderedDict([
                    ('type', 'object'),
                    ('description', 'Additional error details')
                ]))
            ])),
            ('required', ['error', 'code'])
        ])
        
        # Save the complete OpenAPI specification
        output_file = 'exports/openapi_specs/seniorcare_api3.0.yaml'
        
        # Custom YAML representer to maintain order and style
        def represent_ordereddict(dumper, data):
            return dumper.represent_dict(data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict)
        
        with open(output_file, 'w', encoding='utf-8') as file:
            yaml.dump(openapi_spec, file, default_flow_style=False, allow_unicode=True, 
                     indent=2, width=1000, sort_keys=False)
        
        print(f"\n🎉 OpenAPI specification saved to {output_file}")
        print(f"Successfully processed {len(processed_tables)} tables:")
        for table in processed_tables:
            print(f"   - {table}")
        
        connection.close()
        print("\n✅ Export completed successfully!")
        print(f"\nGenerated file: {output_file}")
        print("\n You can now:")
        print("   - View it in Swagger UI")
        print("   - Import it into Postman")  
        print("   - Generate API client code")
        print("   - Use it for API documentation")
        
    except Exception as e:
        print(f"❌ Error during export: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":

    export_mysql_to_openapi_yaml()
