from setuptools import find_packages, setup
import os
package_name = 'amr_khaled'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        (os.path.join('share', package_name), [os.path.join(package_name, 'real_or_fake_model.pt')]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omar',
    maintainer_email='omargomaa9102006@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "scroll_detection_node = amr_khaled.scroll_detection_node:main",
            "controller_node = amr_khaled.controller_node:main",
            "eyes = amr_khaled.eyes_node:main",
            "autonomous_drive_node = amr_khaled.autonomous_drive_node:main",
            "manual_drive_node = amr_khaled.manual_drive_node:main",
        ],
    },
)
