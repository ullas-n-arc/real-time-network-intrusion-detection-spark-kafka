// MongoDB initialization script
// Creates database and collections with indexes

db = db.getSiblingDB('nids_db');

// Create alerts collection with schema validation
db.createCollection('intrusion_alerts', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['is_attack', 'processed_at'],
            properties: {
                is_attack: {
                    bsonType: 'bool',
                    description: 'Whether this is an attack'
                },
                attack_type: {
                    bsonType: 'string',
                    description: 'Type of attack detected'
                },
                severity: {
                    enum: ['NONE', 'LOW', 'MEDIUM', 'HIGH'],
                    description: 'Severity level'
                },
                binary_prediction: {
                    bsonType: 'double',
                    description: 'Binary classifier prediction'
                },
                multiclass_prediction: {
                    bsonType: 'double',
                    description: 'Multiclass classifier prediction'
                },
                processed_at: {
                    bsonType: 'date',
                    description: 'When the record was processed'
                },
                inserted_at: {
                    bsonType: 'date',
                    description: 'When the record was inserted into MongoDB'
                },
                source_ip: {
                    bsonType: 'string',
                    description: 'Source IP address'
                },
                destination_ip: {
                    bsonType: 'string',
                    description: 'Destination IP address'
                }
            }
        }
    }
});

// Create indexes
db.intrusion_alerts.createIndex({ "processed_at": -1 });
db.intrusion_alerts.createIndex({ "severity": 1 });
db.intrusion_alerts.createIndex({ "attack_type": 1 });
db.intrusion_alerts.createIndex({ "is_attack": 1 });
db.intrusion_alerts.createIndex({ "severity": 1, "processed_at": -1 });

// Create statistics collection
db.createCollection('alert_statistics');

// Create a user for the application
db.createUser({
    user: 'nids_user',
    pwd: 'nids_password',
    roles: [
        { role: 'readWrite', db: 'nids_db' }
    ]
});

print('MongoDB initialization complete!');
