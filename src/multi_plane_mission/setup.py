from glob import glob

from setuptools import setup

package_name = 'multi_plane_mission'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='raft',
    maintainer_email='raft@todo.todo',
    description='Multi plane mission package',
    license='TODO',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mission_node = multi_plane_mission.mission_node:main',
            'single_plane_test = multi_plane_mission.single_plane_test:main',
        ],
    },
)
