import pymysql
import yaml
import os
import re
from datetime import datetime, date, time
from decimal import Decimal

def is_valid_table_name(table_name):
    """Check if table name is valid (no spaces, special characters, etc.)"""
    return bool(re.match(r'^[a-zA-Z0-9_]+$', table_name.strip()))

def table_exists(cursor, table_name):
    """Check if a table actually exists in the database"""
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        return True
    except pymysql.err.ProgrammingError:
        return False

def convert_mysql_value(value):
    """Convert MySQL values to YAML-friendly formats"""
    if value is None:
        return None
    elif isinstance(value, (datetime, date, time)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.hex()  # Convert to hex string if not UTF-8
    else:
        return value

def export_mysql_to_yaml():
    try:
        print("Connecting to MySQL database...")
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='YourDatabasePassword',
            database='YourDatabase',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        print("Connected successfully!")
        
        # Get all table names
        print("Getting table names...")
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
            
            if is_valid_table_name(table_name) and table_exists(cursor, table_name):
                valid_tables.append(table_name)
            else:
                invalid_tables.append(table_name)
                print(f"Skipping invalid/non-existent table: '{table_name}'")
        
        if not valid_tables:
            print("No valid tables found!")
            return
        
        print(f"Found {len(valid_tables)} valid tables: {valid_tables}")
        if invalid_tables:
            print(f"Skipped {len(invalid_tables)} invalid tables: {invalid_tables}")
        
        # Create data directory for YAML files
        output_dir = 'exports/yaml_data'
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created '{output_dir}' directory")
        
        exported_files = []
        total_records = 0
        
        for table_name in valid_tables:
            try:
                print(f"\nProcessing table: {table_name}")
                
                # Get all data from table
                cursor.execute(f"SELECT * FROM `{table_name}`")
                rows = cursor.fetchall()
                print(f"Found {len(rows)} rows")
                
                file_path = f'{output_dir}/{table_name}.yaml'
                
                if len(rows) == 0:
                    print(f"Table {table_name} is empty, creating empty YAML file")
                    with open(file_path, 'w', encoding='utf-8') as file:
                        yaml.dump([], file, default_flow_style=False, allow_unicode=True, indent=2)
                    exported_files.append((table_name, file_path, 0))
                    continue
                
                # Get column names
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns_info = cursor.fetchall()
                columns = [col[0] for col in columns_info]
                print(f"Columns: {columns}")
                
                # Convert to list of dictionaries with proper data type handling
                table_data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        # Handle different data types properly
                        value = convert_mysql_value(row[i])
                        row_dict[col_name] = value
                    table_data.append(row_dict)
                
                # Save to YAML file with better formatting
                with open(file_path, 'w', encoding='utf-8') as file:
                    yaml.dump(table_data, file, 
                             default_flow_style=False, 
                             allow_unicode=True, 
                             indent=2,
                             width=1000,
                             sort_keys=False)
                
                print(f"Exported {len(table_data)} records to {file_path}")
                exported_files.append((table_name, file_path, len(table_data)))
                total_records += len(table_data)
                
            except Exception as table_error:
                print(f"Error processing table {table_name}: {table_error}")
                continue
        
        connection.close()
        
        # Generate summary
        print(f"\nExport completed successfully!")
        print("=" * 60)
        print(f"Summary:")
        print(f"  Total tables processed: {len(exported_files)}")
        print(f"  Total records exported: {total_records}")
        print(f"  Output directory: {output_dir}")
        
        # Verify the files were created and show detailed info
        print(f"\nGenerated YAML files:")
        for table_name, file_path, record_count in exported_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                size_str = f"{file_size:,} bytes" if file_size < 1024 else f"{file_size/1024:.1f} KB"
                print(f"  - {table_name}.yaml ({record_count} records, {size_str})")
            else:
                print(f"  - {table_name}.yaml (FILE NOT FOUND!)")
        
        # Create metadata file
        metadata = {
            'export_info': {
                'database': 'seniorcare',
                'export_date': datetime.now().isoformat(),
                'total_tables': len(exported_files),
                'total_records': total_records,
                'tables': [
                    {
                        'name': table_name,
                        'file': f"{table_name}.yaml",
                        'records': record_count
                    }
                    for table_name, _, record_count in exported_files
                ]
            }
        }
        
        metadata_path = f'{output_dir}/export_metadata.yaml'
        with open(metadata_path, 'w', encoding='utf-8') as file:
            yaml.dump(metadata, file, default_flow_style=False, allow_unicode=True, indent=2)
        
        print(f"\nMetadata file created: {metadata_path}")
        
        print(f"\nUsage:")
        print(f"  - Use these YAML files as data sources")
        print(f"  - Import into other systems")
        print(f"  - Use with YAML-based databases")
        print(f"  - Convert to other formats (JSON, CSV, etc.)")
        
    except Exception as e:
        print(f"Error during export: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":

    export_mysql_to_yaml()
