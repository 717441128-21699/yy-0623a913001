from database import SessionLocal, engine, Base
from models import Product, Clinic
from schemas import ProductCreate, ClinicCreate
from services import ProductService
from services.order_service import ClinicService


def init_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("开始初始化数据...")

        product_service = ProductService(db)
        clinic_service = ClinicService(db)

        print("\n=== 创建诊所 ===")
        clinics = [
            ClinicCreate(
                name="阳光口腔诊所",
                contact_person="张医生",
                phone="13800138001",
                address="北京市朝阳区建国路88号",
                remark="VIP客户，每周二补货"
            ),
            ClinicCreate(
                name="康美牙科中心",
                contact_person="李护士",
                phone="13800138002",
                address="北京市海淀区中关村大街1号",
                remark="常有急诊订单"
            ),
            ClinicCreate(
                name="爱牙仕口腔医院",
                contact_person="王主任",
                phone="13800138003",
                address="北京市西城区金融街10号",
                remark="大客户，月结"
            )
        ]
        for c in clinics:
            clinic = clinic_service.create(c)
            print(f"  创建诊所: {clinic.name} (ID: {clinic.id})")

        print("\n=== 创建产品目录 ===")
        products = [
            ProductCreate(
                name="纳米树脂",
                brand="3M",
                specification="A2",
                unit="支",
                category="树脂材料",
                stock=50,
                price=180.0,
                aliases=["3M树脂", "光固化树脂", "补牙树脂"],
                similar_products=[2],
                remark="常用色号"
            ),
            ProductCreate(
                name="纳米树脂",
                brand="3M",
                specification="A3",
                unit="支",
                category="树脂材料",
                stock=30,
                price=180.0,
                aliases=["3M树脂A3", "树脂A3"],
                similar_products=[1],
                remark="偏黄色号"
            ),
            ProductCreate(
                name="纳米树脂",
                brand="科尔",
                specification="A2",
                unit="支",
                category="树脂材料",
                stock=20,
                price=160.0,
                aliases=["科尔树脂", "Kerr树脂"],
                similar_products=[1],
                remark="可替代3M A2"
            ),
            ProductCreate(
                name="碧兰麻",
                brand="碧兰",
                specification="1.7ml/支",
                unit="支",
                category="麻醉药品",
                stock=100,
                price=25.0,
                aliases=["阿替卡因", "碧蓝麻"],
                similar_products=[5]
            ),
            ProductCreate(
                name="斯康杜尼",
                brand="斯康杜尼",
                specification="2% 1.8ml",
                unit="支",
                category="麻醉药品",
                stock=0,
                price=15.0,
                aliases=["甲哌卡因", "斯康"],
                similar_products=[4],
                remark="暂时缺货，预计3天后到货"
            ),
            ProductCreate(
                name="一次性注射器",
                brand="米沙瓦",
                specification="30G 短针头",
                unit="盒",
                category="器械耗材",
                stock=15,
                price=85.0,
                aliases=["麻醉针头", "30G针头", "细针头"],
                similar_products=[7],
                remark="每盒100支"
            ),
            ProductCreate(
                name="一次性注射器",
                brand="米沙瓦",
                specification="27G 长针头",
                unit="盒",
                category="器械耗材",
                stock=20,
                price=80.0,
                aliases=["麻醉长针头", "27G针头"],
                similar_products=[6],
                remark="每盒100支"
            ),
            ProductCreate(
                name="洁牙机工作尖",
                brand="EMS",
                specification="P1",
                unit="支",
                category="器械耗材",
                stock=5,
                price=120.0,
                aliases=["洁牙头", "洗牙头", "P1工作尖"],
                similar_products=[9],
                remark="EMS原装"
            ),
            ProductCreate(
                name="洁牙机工作尖",
                brand="啄木鸟",
                specification="P1",
                unit="支",
                category="器械耗材",
                stock=40,
                price=35.0,
                aliases=["洁牙头", "啄木鸟工作尖"],
                similar_products=[8],
                remark="通用型，可替代EMS"
            ),
            ProductCreate(
                name="高速手机",
                brand="NSK",
                specification="PANA AIR",
                unit="把",
                category="牙科设备",
                stock=8,
                price=850.0,
                aliases=["涡轮手机", "高速牙钻"],
                similar_products=[],
                remark="原装进口"
            ),
            ProductCreate(
                name="车针",
                brand="MANI",
                specification="金刚砂 FG-102",
                unit="板",
                category="器械耗材",
                stock=25,
                price=45.0,
                aliases=["马尼车针", "备牙车针"],
                similar_products=[]
            ),
            ProductCreate(
                name="磷酸酸蚀剂",
                brand="3M",
                specification="37% 5ml",
                unit="瓶",
                category="粘接材料",
                stock=0,
                price=120.0,
                aliases=["酸蚀剂", "3M酸蚀"],
                similar_products=[],
                remark="缺货，预计下周到货"
            )
        ]

        for p in products:
            product = product_service.create(p)
            print(f"  创建产品: {product.brand} {product.name} {product.specification} (ID: {product.id}, 库存: {product.stock})")

        print("\n=== 数据初始化完成 ===")
        print(f"  诊所总数: {len(clinics)}")
        print(f"  产品总数: {len(products)}")

    finally:
        db.close()


if __name__ == "__main__":
    init_database()
