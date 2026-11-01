import os
import sqlite3
from typing import List, Dict, Any, Optional
from app.database.connection import DatabaseConnection

class KnowledgePacker:
    def __init__(self, db_path: Optional[str] = None, output_dir: str = "ai_workspace/packed_context"):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_manager = DatabaseConnection(db_path)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Límites estrictos para inyección limpia en Contexto de Proyectos de Claude
        self.MIN_BYTES = int(1.5 * 1024 * 1024) 
        self.MAX_BYTES = int(2.5 * 1024 * 1024) 

    def _fetch_all_data(self) -> Dict[str, List[sqlite3.Row]]:
        data_payload = {"trends": [], "formulas": [], "traffic": []}
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.*, v.title as video_title, v.channel_name, v.platform 
                FROM product_trends t LEFT JOIN video_sources v ON t.video_id = v.video_id ORDER BY t.validated_at DESC
            """)
            data_payload["trends"] = cursor.fetchall()
            
            cursor.execute("""
                SELECT f.*, v.title as video_title, v.channel_name 
                FROM conversion_formulas f LEFT JOIN video_sources v ON f.video_id = v.video_id ORDER BY f.id DESC
            """)
            data_payload["formulas"] = cursor.fetchall()
            
            cursor.execute("""
                SELECT o.*, v.title as video_title, v.channel_name 
                FROM operations_traffic o LEFT JOIN video_sources v ON o.video_id = v.video_id ORDER BY o.id DESC
            """)
            data_payload["traffic"] = cursor.fetchall()
            
        return data_payload

    def _build_xml_node(self, tag_name: str, attributes: Dict[str, Any], content: str) -> str:
        attr_str = " ".join([f'{k}="{v}"' for k, v in attributes.items() if v is not None])
        opening_tag = f"<{tag_name} {attr_str}>" if attr_str else f"<{tag_name}>"
        return f"{opening_tag}\n{content}</{tag_name}>\n"

    def format_row_to_xml(self, table_type: str, row: sqlite3.Row) -> str:
        """Sanitiza y encapsula datos usando bloques seguros CDATA contra inyecciones de código."""
        if table_type == "trend":
            content = (
                f"  <product_name>{row['product_name']}</product_name>\n"
                f"  <niche>{row['niche']}</niche>\n"
                f"  <wow_factor><![CDATA[{row['wow_factor']}]]></wow_factor>\n"
                f"  <margin_multiplier>{row['estimated_margin']}x</margin_multiplier>\n"
                f"  <competitor_vulnerabilities><![CDATA[{row['competitor_weaknesses']}]]></competitor_vulnerabilities>\n"
            )
            attrs = {"id": row['id'], "source_video": row['video_title'], "channel": row['channel_name']}
            return self._build_xml_node("market_item", attrs, content)
            
        elif table_type == "formula":
            content = (
                f"  <category>{row['category']}</category>\n"
                f"  <framework>{row['framework_name']}</framework>\n"
                f"  <raw_structure><![CDATA[{row['raw_structure']}]]></raw_structure>\n"
                f"  <persuasion_triggers>{row['persuasion_triggers']}</persuasion_triggers>\n"
                f"  <recommended_stack>{row['recommended_apps']}</recommended_stack>\n"
            )
            attrs = {"id": row['id'], "source_video": row['video_title']}
            return self._build_xml_node("conversion_framework", attrs, content)
            
        elif table_type == "traffic":
            content = (
                f"  <traffic_source>{row['traffic_source']}</traffic_source>\n"
                f"  <scaling_strategy><![CDATA[{row['scaling_strategy']}]]></scaling_strategy>\n"
                f"  <logistics_notes><![CDATA[{row['logistics_notes']}]]></logistics_notes>\n"
                f"  <legal_and_gateways><![CDATA[{row['gateways_legal']}]]></legal_and_gateways>\n"
            )
            attrs = {"id": row['id'], "source_video": row['video_title']}
            return self._build_xml_node("traffic_protocol", attrs, content)
            
        return ""

    def generate_prompt_maestro_wrapper(self, block_index: int, inner_content: str) -> str:
        """Inyecta el cascarón de gobernanza del Prompt Maestro Corporativo KDP/GEM OS."""
        return (
            f"<!-- SYSTEM INSTRUCTION: PROMPT MAESTRO DE CONTEXTO DENSE E-COMMERCE -->\n"
            f"<gem_os_knowledge_vault version='3.7.2' block_id='{block_index}'>\n"
            f"<metadata>\n"
            f"  <purpose>Inyección masiva de contexto verificado para orquestación de tiendas Shopify</purpose>\n"
            f"  <architecture_origin>Elite Corporate KDP-Master-Suite Base</architecture_origin>\n"
            f"</metadata>\n\n"
            f"<compressed_knowledge_payload>\n"
            f"{inner_content}"
            f"</compressed_knowledge_payload>\n"
            f"</gem_os_knowledge_vault>"
        )

    def pack_context(self) -> List[str]:
        raw_data = self._fetch_all_data()
        generated_blocks = []
        current_block_content = ""
        block_counter = 1
        
        items_queue = []
        for row in raw_data["trends"]: items_queue.append(("trend", row))
        for row in raw_data["formulas"]: items_queue.append(("formula", row))
        for row in raw_data["traffic"]: items_queue.append(("traffic", row))
        
        for item_type, row in items_queue:
            xml_segment = self.format_row_to_xml(item_type, row)
            test_full_prompt = self.generate_prompt_maestro_wrapper(block_counter, current_block_content + xml_segment)
            current_bytes = len(test_full_prompt.encode('utf-8'))
            
            if current_bytes >= self.MAX_BYTES:
                final_prompt = self.generate_prompt_maestro_wrapper(block_counter, current_block_content)
                file_name = f"knowledge_block_{block_counter:03d}.txt"
                full_path = os.path.join(self.output_dir, file_name)
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(final_prompt)
                
                generated_blocks.append(full_path)
                block_counter += 1
                current_block_content = xml_segment
            else:
                current_block_content += xml_segment

        if current_block_content:
            final_prompt = self.generate_prompt_maestro_wrapper(block_counter, current_block_content)
            file_name = f"knowledge_block_{block_counter:03d}.txt"
            full_path = os.path.join(self.output_dir, file_name)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(final_prompt)
            generated_blocks.append(full_path)

        return generated_blocks
