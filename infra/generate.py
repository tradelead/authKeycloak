from troposphere import Tags, ImportValue, Parameter, Sub, GetAtt, Ref, Join, Output, Export
from troposphere import Template
from troposphere import iam, ec2, ecs, elasticloadbalancingv2

t = Template()
t.add_version('2010-09-09')
t.add_transform('AWS::Serverless-2016-10-31')

# Parameters

t.add_parameter(Parameter('CoreStack', Type='String'))
t.add_parameter(Parameter('MySQLDbName', Type='String'))
t.add_parameter(Parameter('MySQLUser', Type='String'))
t.add_parameter(Parameter('MySQLPass', Type='String'))
t.add_parameter(Parameter('KeycloakUser', Type='String'))
t.add_parameter(Parameter('KeycloakPassword', Type='String'))
t.add_parameter(Parameter('KeycloakImage', Type='String'))

# ECS
keycloakTargetGroup = t.add_resource(elasticloadbalancingv2.TargetGroup(
    'KeycloakTargetGroup',
    Port = '80',
    Protocol = 'HTTP',
    VpcId = ImportValue(Sub('${CoreStack}-VPC-ID')),
    TargetType = 'ip',
    HealthCheckPath = '/auth/realms/main',
    HealthCheckProtocol = 'HTTP',
    HealthCheckIntervalSeconds = 240,
    HealthyThresholdCount = 5,
    UnhealthyThresholdCount = 5,
))

keycloakListenerRule = t.add_resource(elasticloadbalancingv2.ListenerRule(
    'KeycloakListenerRule',
    ListenerArn = ImportValue(Sub('${CoreStack}-ALB-Web-Listener')),
    Priority = 10,
    Conditions = [elasticloadbalancingv2.Condition(
        Field = 'path-pattern',
        Values = ['/auth', '/auth*']
    )],
    Actions = [elasticloadbalancingv2.Action(
        Type = 'forward',
        TargetGroupArn = keycloakTargetGroup.Ref(),
    )]
))

keycloakTask = t.add_resource(ecs.TaskDefinition(
    'KeycloakTask',
    ContainerDefinitions = [ecs.ContainerDefinition(
        'KeycloakContainer',
        Name = 'keycloak',
        Image = Ref('KeycloakImage'),
        Environment = [
            ecs.Environment(Name = 'KEYCLOAK_USER', Value = Ref('KeycloakUser')),
            ecs.Environment(Name = 'KEYCLOAK_PASSWORD', Value = Ref('KeycloakImage')),
            ecs.Environment(Name = 'DB_VENDOR', Value = 'mysql'),
            ecs.Environment(Name = 'DB_ADDR', Value = ImportValue(Sub('${CoreStack}-MySQL-Address'))),
            ecs.Environment(Name = 'DB_PORT', Value = ImportValue(Sub('${CoreStack}-MySQL-Port'))),
            ecs.Environment(Name = 'DB_DATABASE', Value = Ref('MySQLDbName')),
            ecs.Environment(Name = 'DB_USER', Value = Ref('MySQLUser')),
            ecs.Environment(Name = 'DB_PASSWORD', Value = Ref('MySQLPass')),
        ],
        MemoryReservation = '512',
        PortMappings = [ecs.PortMapping(
            ContainerPort = 8080,
        )],
        HealthCheck = ecs.HealthCheck(
            Command = ['/bin/bash -c "curl -f http://localhost:8080/auth/realms/main || exit 1"'],
            StartPeriod = 120,
            Retries = 10,
            Interval = 60,
        ),
        LogConfiguration = ecs.LogConfiguration(
            LogDriver = 'awslogs',
            Options = {
                "awslogs-group": Sub('${AWS::StackName}-KeycloakTask'),
                "awslogs-region": Ref("AWS::Region"),
                "awslogs-stream-prefix": "ecs",
            },
        ),
    )],
    NetworkMode = 'awsvpc',
))

keycloakServiceSG = t.add_resource(ec2.SecurityGroup(
    'KeycloakSecurityGroup', 
    GroupDescription = 'Keycloak Service SG',
    VpcId = ImportValue(Sub('${CoreStack}-VPC-ID')),
    SecurityGroupIngress = [{
        'IpProtocol': 'tcp',
        'FromPort': 8080,
        'ToPort': 8080,
        'SourceSecurityGroupId': ImportValue(Sub('${CoreStack}-LoadBalancer-SG-ID')),
    }],
))

keycloakService = t.add_resource(ecs.Service(
    'KeycloakService',
    Cluster = ImportValue(Sub('${CoreStack}-ECS-Cluster')),
    TaskDefinition = keycloakTask.Ref(),
    DesiredCount = 1,
    LoadBalancers = [ecs.LoadBalancer(
        ContainerName = 'keycloak',
        ContainerPort = 8080,
        TargetGroupArn = keycloakTargetGroup.Ref(),
    )],
    NetworkConfiguration = ecs.NetworkConfiguration(
        AwsvpcConfiguration = ecs.AwsvpcConfiguration(
            SecurityGroups=[
                ImportValue(Sub('${CoreStack}-RDS-Access-SG-ID')),
                keycloakServiceSG.GetAtt('GroupId'),
            ],
            Subnets=[ImportValue(Sub('${CoreStack}-SubnetID'))],
        ),
    )
))

# Save File

with open('template.yml', 'w') as f:
    f.write(t.to_yaml())
