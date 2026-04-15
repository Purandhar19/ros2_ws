from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    fcu_url = LaunchConfiguration('fcu_url')
    gcs_url = LaunchConfiguration('gcs_url')

    return LaunchDescription([
        DeclareLaunchArgument(
            'fcu_url',
            default_value='udp://@127.0.0.1:14540',
            description='MAVLink endpoint for the aircraft',
        ),
        DeclareLaunchArgument(
            'gcs_url',
            default_value='',
            description='Optional MAVLink forwarding endpoint for QGC, e.g. udp://@127.0.0.1:14550',
        ),
        Node(
            package='mavros',
            executable='mavros_node',
            namespace='plane1',
            name='mavros',
            output='screen',
            parameters=[{
                'fcu_url': fcu_url,
                'gcs_url': gcs_url,
                'tgt_system': 1,
            }],
        ),
        Node(
            package='multi_plane_mission',
            executable='mission_node',
            namespace='plane1',
            name='mission',
            output='screen',
            parameters=[{
                'mavros_ns': '/plane1/mavros',
                'takeoff_lat': 38.3148,
                'takeoff_lon': -76.5489,
                'takeoff_alt': 60.0,
                'waypoint_lats': [38.3150, 38.3155, 38.3160],
                'waypoint_lons': [-76.5495, -76.5500, -76.5490],
                'waypoint_alts': [60.0, 60.0, 60.0],
            }],
        ),
    ])
