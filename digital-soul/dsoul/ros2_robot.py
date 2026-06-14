"""ROS2 机器人驱动样例：把数字分身的动作映射到 ROS2 话题。

需要 ROS2（rclpy）。未安装时本文件仍可正常 import，仅在实例化 Ros2Robot 时
给出清晰报错——这样不影响框架其余部分在普通机器上运行/测试。

话题约定（按你的机器人实际情况改）：
  /cmd_vel        geometry_msgs/Twist   底盘移动
  /soul/speech    std_msgs/String       语音播报
  /soul/look_at   std_msgs/String       注视目标
  /soul/mode      std_msgs/String       模式（如 guard:小婷）

用法：
    from dsoul.loader import build_agent
    from dsoul.ros2_robot import Ros2Robot
    agent = build_agent(robot=Ros2Robot())   # 其余逻辑零改动
"""

from __future__ import annotations

from .actions import RobotInterface


class Ros2Robot(RobotInterface):
    def __init__(self, node_name: str = "digital_soul") -> None:
        try:
            import rclpy
            from geometry_msgs.msg import Twist
            from rclpy.node import Node
            from std_msgs.msg import String
        except Exception as e:  # 没有 ROS2 环境时给出清晰指引
            raise RuntimeError(
                "需要 ROS2 与 rclpy。先 `source /opt/ros/<distro>/setup.bash` 再使用。"
            ) from e

        self._rclpy = rclpy
        self._String = String
        self._Twist = Twist

        if not rclpy.ok():
            rclpy.init()
        self.node = Node(node_name)
        self.pub_speech = self.node.create_publisher(String, "/soul/speech", 10)
        self.pub_look = self.node.create_publisher(String, "/soul/look_at", 10)
        self.pub_mode = self.node.create_publisher(String, "/soul/mode", 10)
        self.pub_cmd = self.node.create_publisher(Twist, "/cmd_vel", 10)

    def say(self, text: str) -> None:
        msg = self._String()
        msg.data = text
        self.pub_speech.publish(msg)
        self.node.get_logger().info(f"say: {text}")

    def move(self, direction: str, meters: float = 1.0) -> None:
        tw = self._Twist()
        tw.linear.x = {"前": 0.2, "后": -0.2}.get(direction, 0.2)  # m/s（真实实现应按距离计时停止）
        self.pub_cmd.publish(tw)
        self.node.get_logger().info(f"move {direction} {meters}m")

    def look_at(self, target: str) -> None:
        msg = self._String()
        msg.data = target
        self.pub_look.publish(msg)

    def protect(self, target: str) -> None:
        msg = self._String()
        msg.data = f"guard:{target}"
        self.pub_mode.publish(msg)
        self.node.get_logger().info(f"protect {target}")

    def shutdown(self) -> None:
        self.node.destroy_node()
        if self._rclpy.ok():
            self._rclpy.shutdown()
