from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    plane1_mavros = Node(
        package='mavros',
        executable='mavros_node',
        namespace='plane1',
        output='screen',
        parameters=[{
            'fcu_url': 'udp://@127.0.0.1:14540'
        }]
    )

    plane2_mavros = Node(
        package='mavros',
        executable='mavros_node',
        namespace='plane2',
        output='screen',
        parameters=[{
            'fcu_url': 'udp://@127.0.0.1:14541'
        }]
    )

    mission_node = Node(
        package='multi_plane_mission',
        executable='mission_node',
        output='screen'
    )

    return LaunchDescription([
        plane1_mavros,
        plane2_mavros,
        mission_node
    ])
