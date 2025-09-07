# Generate-OpenAPI-Document-Tools
Generate OpenAPI Document Tools
# MysqlToYaml

A Python tool for converting MySQL database schemas to YAML format and generating OpenAPI specifications.

## Features

- **MySQL to YAML Export**: Export complete database tables to individual YAML files
- **OpenAPI Generation**: Generate comprehensive OpenAPI 3.0 specifications from database schemas
- **Multiple Output Formats**: Create both consolidated and individual API specifications
- **YAML Database Interface**: Work with exported data using a YAML-based database abstraction

## Files

- `mysql_to_yaml.py` - Exports MySQL tables to YAML files
- `mysql_to_openapi.py` - Generates OpenAPI specifications from database schema
- `mysql_to_individual_openapi.py` - Creates individual OpenAPI files per table
- `yaml_database.py` - YAML database abstraction layer
- `main.py` - Example usage of the YAML database
- `debug_mysql.py` - MySQL debugging utilities

## Usage

### Export MySQL to YAML
```bash
python mysql_to_yaml.py
```

### Generate OpenAPI Specification
```bash
python mysql_to_openapi.py
```

### Generate Individual API Files
```bash
python mysql_to_individual_openapi.py
```

## Output

- **YAML files**: Exported to `data/` directory
- **OpenAPI specs**: Generated in `openapi_specs/` directory

## Requirements

- Python 3.x
- PyMySQL
- PyYAML

## Installation

```bash
pip install pymysql pyyaml
```

## Configuration

Update database connection settings in the Python files:
- Host: localhost
- Database: seniorcare
- Update credentials as needed
  
## Tips

common error：
Make sure you input your name(default:root),password and database,including in the middle of the code.
