from pydantic import Field
from rag.tools.base import BaseTool
from langchain.output_parsers import PydanticToolsParser


class ToolOrder(BaseTool):
    """
    查询用户的订单信息
    """
    orderID: int = Field(description="订单ID")

    def exec(self):
        order_id_tail = int(self.orderID) % 10
        if order_id_tail == 1:
            return {
                "order_id": self.orderID,
                "status": "运输中",
                "price": "13.5元"
            }
        elif order_id_tail == 2:
            return {
                "order_id": self.orderID,
                "status": "未支付",
                "price": "9.9元"
            }
        else:
            return {
                "order_id": self.orderID,
                "status": "已完成",
                "price": "199元"
            }
