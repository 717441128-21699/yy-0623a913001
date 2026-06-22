from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
import jieba

from models import Product
from schemas import ProductCreate, ProductUpdate, ProductMatchResult


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def ratio(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 100.0
    return (1 - distance / max_len) * 100


def partial_ratio(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    if len(s1) <= len(s2):
        short, long = s1, s2
    else:
        short, long = s2, s1
    max_score = 0.0
    len_short = len(short)
    for i in range(len(long) - len_short + 1):
        substr = long[i:i + len_short]
        score = ratio(short, substr)
        if score > max_score:
            max_score = score
    return max_score


def token_sort_ratio(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    tokens1 = sorted(jieba.lcut(s1))
    tokens2 = sorted(jieba.lcut(s2))
    sorted1 = ''.join(tokens1)
    sorted2 = ''.join(tokens2)
    return ratio(sorted1, sorted2)


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, product_in: ProductCreate) -> Product:
        db_product = Product(**product_in.model_dump(exclude={"id", "created_at", "updated_at"}))
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def list(self, skip: int = 0, limit: int = 100, category: str = None, keyword: str = None) -> Tuple[List[Product], int]:
        query = self.db.query(Product)
        if category:
            query = query.filter(Product.category == category)
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.filter(
                (Product.name.like(keyword_pattern)) |
                (Product.brand.like(keyword_pattern)) |
                (Product.specification.like(keyword_pattern))
            )
        total = query.count()
        products = query.offset(skip).limit(limit).all()
        return products, total

    def update(self, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
        db_product = self.get_by_id(product_id)
        if not db_product:
            return None
        update_data = product_in.model_dump(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        for field, value in update_data.items():
            setattr(db_product, field, value)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def delete(self, product_id: int) -> bool:
        db_product = self.get_by_id(product_id)
        if not db_product:
            return False
        self.db.delete(db_product)
        self.db.commit()
        return True

    def get_all_products_for_match(self) -> List[Product]:
        return self.db.query(Product).all()

    def _parse_quantity(self, text: str) -> Tuple[Optional[float], Optional[str], str]:
        import re

        chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '廿': 20, '卅': 30, '百': 100, '千': 1000
        }

        def chinese_to_num(chinese_str: str) -> Optional[float]:
            if chinese_str in chinese_num_map:
                return float(chinese_num_map[chinese_str])
            try:
                total = 0
                temp = 0
                for char in chinese_str:
                    if char in chinese_num_map:
                        val = chinese_num_map[char]
                        if val >= 10:
                            if temp == 0:
                                temp = 1
                            total += temp * val
                            temp = 0
                        else:
                            temp = val
                total += temp
                return float(total) if total > 0 else None
            except:
                return None

        unit_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(支|根|个|只|盒|包|瓶|袋|箱)', '支'),
            (r'([零一二两三四五六七八九十廿卅百千]+)\s*(支|根|个|只|盒|包|瓶|袋|箱)', '支'),
            (r'(\d+(?:\.\d+)?)\s*(板|片|条)', '板'),
            (r'([零一二两三四五六七八九十廿卅百千]+)\s*(板|片|条)', '板'),
        ]
        remaining_text = text
        quantity = None
        unit = None
        for pattern, default_unit in unit_patterns:
            match = re.search(pattern, text)
            if match:
                num_str = match.group(1)
                if num_str.isdigit() or '.' in num_str:
                    quantity = float(num_str)
                else:
                    parsed = chinese_to_num(num_str)
                    if parsed is not None:
                        quantity = parsed
                unit = match.group(2) or default_unit
                remaining_text = re.sub(pattern, '', text).strip()
                break
        return quantity, unit, remaining_text

    def _find_same_name_diff_spec(self, product: Product, all_products: List[Product]) -> List[Product]:
        same_name = []
        for p in all_products:
            if p.id != product.id and p.name == product.name and p.specification != product.specification:
                same_name.append(p)
        return same_name

    def fuzzy_match(self, raw_text: str, threshold: int = 60) -> ProductMatchResult:
        quantity, unit, cleaned_text = self._parse_quantity(raw_text)
        all_products = self.get_all_products_for_match()

        if not all_products:
            return ProductMatchResult(
                matched=False,
                confidence=0,
                raw_text=raw_text,
                parsed_quantity=quantity,
                parsed_unit=unit,
                suggestion="产品目录为空，请先添加产品"
            )

        match_candidates = []
        for product in all_products:
            search_fields = [product.name, product.brand, product.specification]
            search_fields.extend(product.aliases or [])
            scores = []
            for field in search_fields:
                if field:
                    scores.append(partial_ratio(cleaned_text, field))
                    scores.append(token_sort_ratio(cleaned_text, field))
            if scores:
                max_score = max(scores)
                match_candidates.append((max_score, product))

        match_candidates.sort(key=lambda x: x[0], reverse=True)

        if match_candidates and match_candidates[0][0] >= threshold:
            best_score, best_product = match_candidates[0]
            same_name_products = self._find_same_name_diff_spec(best_product, all_products)

            suggestion = None
            if same_name_products:
                specs = ", ".join([f"{p.brand} {p.specification}" for p in same_name_products])
                suggestion = f"注意：存在同名不同规格产品：{specs}，请确认具体型号"
            elif best_score < 80:
                suggestion = f"匹配度较低({best_score}%)，请人工确认"

            return ProductMatchResult(
                matched=True,
                confidence=best_score / 100,
                product=best_product,
                similar_products=same_name_products,
                raw_text=raw_text,
                parsed_quantity=quantity,
                parsed_unit=unit,
                suggestion=suggestion
            )

        suggestions = []
        for score, product in match_candidates[:5]:
            suggestions.append(f"{product.brand} {product.name} {product.specification} (匹配度{score}%)")

        return ProductMatchResult(
            matched=False,
            confidence=match_candidates[0][0] / 100 if match_candidates else 0,
            raw_text=raw_text,
            parsed_quantity=quantity,
            parsed_unit=unit,
            suggestion="未找到匹配产品，可能的候选：" + "; ".join(suggestions) if suggestions else "未找到匹配产品"
        )

    def batch_match(self, raw_texts: List[str]) -> List[ProductMatchResult]:
        return [self.fuzzy_match(text) for text in raw_texts]

    def get_alternative_products(self, product_id: int) -> List[Product]:
        product = self.get_by_id(product_id)
        if not product:
            return []
        alt_ids = product.similar_products or []
        if not alt_ids:
            return self.db.query(Product).filter(
                Product.category == product.category,
                Product.id != product_id
            ).limit(5).all()
        return self.db.query(Product).filter(Product.id.in_(alt_ids)).all()

    def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        product = self.get_by_id(product_id)
        if not product:
            return None
        product.stock = max(0, product.stock + quantity_change)
        self.db.commit()
        self.db.refresh(product)
        return product
