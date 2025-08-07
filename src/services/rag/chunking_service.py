import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Класс для представления чанка документа"""
    chunk_id: str
    product_id: int
    product_name: str
    text: str
    page_number: Optional[int] = None
    section_type: Optional[str] = None  # 'title', 'content', 'table', 'properties'
    chunk_index: int = 0
    metadata: Optional[Dict[str, Any]] = None

class ChunkingService:
    """
    Сервис для разбивки PDF документов на смысловые чанки.
    
    Учитывая, что у вас документы в среднем 10-11 страниц (макс 40),
    используем гибридную стратегию чанкинга.
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,           # Размер чанка в символах
                 chunk_overlap: int = 200,         # Перекрытие между чанками
                 min_chunk_size: int = 100,        # Минимальный размер чанка
                 max_chunk_size: int = 1500):      # Максимальный размер чанка
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Паттерны для определения разделов
        self.section_patterns = {
            'title': re.compile(r'^[А-ЯЁ\s\d\-\.]{3,50}$', re.MULTILINE),
            'numbered_section': re.compile(r'^\d+\.?\s+[А-ЯЁ]', re.MULTILINE),
            'technical_specs': re.compile(r'(характеристик|свойств|показател|требован)', re.IGNORECASE),
            'application': re.compile(r'(применен|использован|назначен)', re.IGNORECASE),
            'safety': re.compile(r'(безопасн|охран|защит|опасн)', re.IGNORECASE)
        }
        
        # Паттерны для разбивки предложений
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
        
    def chunk_document(self, 
                      product_id: int, 
                      product_name: str, 
                      full_text: str, 
                      page_texts: Optional[List[str]] = None) -> List[DocumentChunk]:
        """
        Основной метод для разбивки документа на чанки.
        
        Args:
            product_id: ID продукта
            product_name: Название продукта
            full_text: Полный текст документа
            page_texts: Список текстов по страницам (опционально)
        
        Returns:
            Список чанков документа
        """
        logger.info(f"Начинаем чанкинг документа для продукта {product_id}: '{product_name}'")
        logger.info(f"Размер текста: {len(full_text)} символов")
        
        if len(full_text) < self.min_chunk_size:
            # Если документ очень маленький, возвращаем его как один чанк
            return [DocumentChunk(
                chunk_id=f"{product_id}_0",
                product_id=product_id,
                product_name=product_name,
                text=full_text,
                chunk_index=0,
                section_type="complete_document"
            )]
        
        chunks = []
        
        # Стратегия 1: Пробуем разбить по семантическим разделам
        semantic_chunks = self._semantic_chunking(full_text)
        
        if semantic_chunks and len(semantic_chunks) > 1:
            logger.info(f"Использован семантический чанкинг: {len(semantic_chunks)} разделов")
            chunks = self._process_semantic_chunks(product_id, product_name, semantic_chunks)
        else:
            # Стратегия 2: Разбивка с учетом предложений и перекрытий
            logger.info("Использован адаптивный чанкинг с перекрытиями")
            chunks = self._adaptive_chunking(product_id, product_name, full_text)
        
        # Добавляем информацию о страницах, если есть
        if page_texts:
            chunks = self._add_page_info(chunks, page_texts)
        
        logger.info(f"Создано {len(chunks)} чанков для продукта {product_id}")
        return chunks
    
    def _semantic_chunking(self, text: str) -> List[Dict[str, Any]]:
        """
        Разбивка текста по семантическим разделам.
        """
        sections = []
        
        # Разбиваем текст на абзацы
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_section = {
            'text': '',
            'type': 'content',
            'start_paragraph': 0
        }
        
        for i, paragraph in enumerate(paragraphs):
            # Определяем тип параграфа
            section_type = self._classify_paragraph(paragraph)
            
            # Если нашли новый раздел и текущий раздел не пустой
            if (section_type in ['title', 'numbered_section'] and 
                current_section['text'] and 
                len(current_section['text']) > self.min_chunk_size):
                
                sections.append(current_section)
                current_section = {
                    'text': paragraph,
                    'type': section_type,
                    'start_paragraph': i
                }
            else:
                # Добавляем к текущему разделу
                if current_section['text']:
                    current_section['text'] += '\n\n' + paragraph
                else:
                    current_section['text'] = paragraph
                    current_section['type'] = section_type
        
        # Добавляем последний раздел
        if current_section['text']:
            sections.append(current_section)
        
        return sections
    
    def _classify_paragraph(self, paragraph: str) -> str:
        """Классифицирует тип параграфа."""
        # Проверяем паттерны
        if self.section_patterns['title'].match(paragraph.strip()):
            return 'title'
        elif self.section_patterns['numbered_section'].match(paragraph.strip()):
            return 'numbered_section'
        elif self.section_patterns['technical_specs'].search(paragraph):
            return 'technical_specs'
        elif self.section_patterns['application'].search(paragraph):
            return 'application'
        elif self.section_patterns['safety'].search(paragraph):
            return 'safety'
        else:
            return 'content'
    
    def _process_semantic_chunks(self, 
                               product_id: int, 
                               product_name: str, 
                               sections: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """
        Обрабатывает семантические разделы в чанки.
        """
        chunks = []
        
        for i, section in enumerate(sections):
            section_text = section['text']
            section_type = section['type']
            
            # Если раздел слишком большой, разбиваем его дополнительно
            if len(section_text) > self.max_chunk_size:
                sub_chunks = self._split_large_section(section_text)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunk = DocumentChunk(
                        chunk_id=f"{product_id}_{i}_{j}",
                        product_id=product_id,
                        product_name=product_name,
                        text=sub_chunk,
                        section_type=section_type,
                        chunk_index=len(chunks),
                        metadata={'is_sub_chunk': True, 'parent_section': i}
                    )
                    chunks.append(chunk)
            else:
                chunk = DocumentChunk(
                    chunk_id=f"{product_id}_{i}",
                    product_id=product_id,
                    product_name=product_name,
                    text=section_text,
                    section_type=section_type,
                    chunk_index=i
                )
                chunks.append(chunk)
        
        return chunks
    
    def _adaptive_chunking(self, 
                         product_id: int, 
                         product_name: str, 
                         text: str) -> List[DocumentChunk]:
        """
        Адаптивная разбивка с учетом предложений и перекрытий.
        """
        chunks = []
        
        # Разбиваем на предложения
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        chunk_index = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # Проверяем, поместится ли предложение в текущий чанк
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
                i += 1
            else:
                # Сохраняем текущий чанк, если он не пустой
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"{product_id}_{chunk_index}",
                        product_id=product_id,
                        product_name=product_name,
                        text=current_chunk.strip(),
                        chunk_index=chunk_index
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Начинаем новый чанк с перекрытием
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                i += 1
        
        # Добавляем последний чанк
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"{product_id}_{chunk_index}",
                product_id=product_id,
                product_name=product_name,
                text=current_chunk.strip(),
                chunk_index=chunk_index
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения."""
        # Простая разбивка по точкам, восклицательным и вопросительным знакам
        sentences = self.sentence_pattern.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str) -> str:
        """Получает текст для перекрытия (последние N символов)."""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Ищем последнее предложение в пределах перекрытия
        overlap_text = text[-self.chunk_overlap:]
        sentence_start = overlap_text.find('. ')
        
        if sentence_start != -1:
            return overlap_text[sentence_start + 2:]
        
        return overlap_text
    
    def _split_large_section(self, text: str) -> List[str]:
        """Разбивает большой раздел на более мелкие части."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.max_chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _add_page_info(self, 
                      chunks: List[DocumentChunk], 
                      page_texts: List[str]) -> List[DocumentChunk]:
        """Добавляет информацию о страницах к чанкам."""
        for chunk in chunks:
            # Простой поиск: ищем, на какой странице встречается начало чанка
            chunk_start = chunk.text[:100]  # Первые 100 символов
            
            for page_num, page_text in enumerate(page_texts, 1):
                if chunk_start in page_text:
                    chunk.page_number = page_num
                    break
        
        return chunks

    def get_chunking_stats(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """Возвращает статистику по чанкам."""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk.text) for chunk in chunks]
        section_types = [chunk.section_type for chunk in chunks if chunk.section_type]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'section_types': list(set(section_types)),
            'pages_covered': list(set(chunk.page_number for chunk in chunks if chunk.page_number))
        }
