# -*- coding: utf-8 -*-
"""
Система достижений для бота поддержки
Обрабатывает проверку и выдачу достижений пользователям
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from achievements_config import ACHIEVEMENTS

logger = logging.getLogger(__name__)

class AchievementSystem:
    """Система управления достижениями"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def check_achievements(self, user_id: int, action: str, **kwargs) -> List[Dict]:
        """
        Проверить и выдать достижения для пользователя
        
        Args:
            user_id: ID пользователя
            action: Тип действия (help_given, rating_reached, messages_sent, etc.)
            **kwargs: Дополнительные параметры для проверки условий
            
        Returns:
            Список новых достижений
        """
        new_achievements = []
        
        try:
            # Получаем все достижения пользователя
            user_achievements = await self.get_user_achievements(user_id)
            user_achievement_ids = {a["achievement_id"] for a in user_achievements}
            
            # Проверяем каждое достижение
            for achievement_id, achievement in ACHIEVEMENTS.items():
                # Пропускаем уже полученные достижения
                if achievement_id in user_achievement_ids:
                    print(f"⏭️ Пропускаем {achievement_id} - уже получено")
                    continue
                
                print(f"🔍 Проверяем достижение: {achievement_id} ({achievement['name']})")
                    
                # Проверяем условие достижения
                if await self._check_achievement_condition(user_id, achievement, action, **kwargs):
                    # Выдаем достижение
                    await self._grant_achievement(user_id, achievement)
                    new_achievements.append(achievement)
                    print(f"🏆 Достижение выдано: {achievement['name']} пользователю {user_id}")
                    logger.info(f"🏆 Achievement granted: {achievement['name']} to user {user_id}")
                else:
                    print(f"❌ Условие не выполнено для {achievement_id}")
            
            print(f"✅ Проверка завершена. Новых достижений: {len(new_achievements)}")
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []
    
    async def _check_achievement_condition(self, user_id: int, achievement: Dict, action: str, **kwargs) -> bool:
        """Проверить условие конкретного достижения"""
        condition = achievement["condition"]
        condition_action = condition["action"]
        
        # Проверяем, что действие соответствует условию (только если action не "all")
        if action != "all" and condition_action != action:
            return False
            
        try:
            if condition_action == "help_given":
                return await self._check_help_given_condition(user_id, condition, **kwargs)
            elif condition_action == "rating_reached":
                return await self._check_rating_reached_condition(user_id, condition, **kwargs)
            elif condition_action == "messages_sent":
                return await self._check_messages_sent_condition(user_id, condition, **kwargs)
            elif condition_action == "registration":
                return await self._check_registration_condition(user_id, condition, **kwargs)
            elif condition_action == "no_complaints":
                return await self._check_no_complaints_condition(user_id, condition, **kwargs)
            elif condition_action == "top_position":
                return await self._check_top_position_condition(user_id, condition, **kwargs)
            else:
                logger.warning(f"Unknown achievement condition: {condition_action}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking achievement condition {achievement['id']}: {e}")
            return False
    
    async def _check_help_given_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие количества оказанной помощи"""
        required_count = condition["count"]
        
        # Получаем количество раз, когда пользователь помог
        result = await self.db.fetchval(
            "SELECT COUNT(*) FROM ratings WHERE user_id = $1",
            user_id
        )
        current_count = result or 0
        
        print(f"🔍 Проверка помощи: пользователь {user_id}, текущее количество: {current_count}, требуется: {required_count}, результат: {current_count >= required_count}")
        
        return current_count >= required_count
    
    
    async def _check_rating_reached_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие достижения рейтинга"""
        required_rating = condition["value"]
        
        result = await self.db.fetchval(
            "SELECT rating FROM ratings WHERE user_id = $1",
            user_id
        )
        current_rating = result or 0
        
        print(f"🔍 Проверка рейтинга: пользователь {user_id}, текущий рейтинг: {current_rating}, требуется: {required_rating}, результат: {current_rating >= required_rating}")
        
        return current_rating >= required_rating
    
    async def _check_messages_sent_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие количества отправленных сообщений"""
        required_count = condition["count"]
        
        result = await self.db.fetchval(
            "SELECT COUNT(*) FROM messages WHERE user_id = $1 AND type = 'support'",
            user_id
        )
        current_count = result or 0
        
        print(f"🔍 Проверка сообщений: пользователь {user_id}, текущее количество: {current_count}, требуется: {required_count}, результат: {current_count >= required_count}")
        
        return current_count >= required_count
    
    
    async def _check_registration_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие регистрации"""
        # Проверяем, есть ли пользователь в базе
        result = await self.db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)",
            user_id
        )
        return result
    
    async def _check_no_complaints_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие отсутствия жалоб"""
        required_rating = condition.get("rating", 0)
        
        # Получаем рейтинг пользователя
        rating = await self.db.fetchval(
            "SELECT rating FROM ratings WHERE user_id = $1",
            user_id
        ) or 0
        
        # Получаем количество жалоб
        complaints = await self.db.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1",
            user_id
        ) or 0
        
        return rating >= required_rating and complaints == 0
    
    async def _check_top_position_condition(self, user_id: int, condition: Dict, **kwargs) -> bool:
        """Проверить условие позиции в топе"""
        required_position = condition["position"]
        
        # Получаем позицию пользователя в рейтинге
        result = await self.db.fetchval("""
            SELECT COUNT(*) + 1
            FROM ratings r
            JOIN users u ON r.user_id = u.user_id
            WHERE u.is_blocked = FALSE AND r.rating > (
                SELECT COALESCE(r2.rating, 0)
                FROM ratings r2
                WHERE r2.user_id = $1
            )
        """, user_id)
        
        return result <= required_position
    
    async def _grant_achievement(self, user_id: int, achievement: Dict):
        """Выдать достижение пользователю"""
        try:
            # Добавляем достижение в базу данных
            await self.db.execute("""
                INSERT INTO user_achievements (user_id, achievement_id, earned_at)
                VALUES ($1, $2, $3)
            """, user_id, achievement["id"], datetime.now())
            
        except Exception as e:
            logger.error(f"Error granting achievement {achievement['id']} to user {user_id}: {e}")
            raise
    
    async def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Получить все достижения пользователя"""
        try:
            result = await self.db.fetch("""
                SELECT ua.achievement_id, ua.earned_at,
                       a.name, a.description, a.icon
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.id
                WHERE ua.user_id = $1
                ORDER BY ua.earned_at DESC
            """, user_id)
            
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Error getting user achievements for {user_id}: {e}")
            return []
    
    
    async def get_achievement_stats(self, user_id: int) -> Dict:
        """Получить статистику достижений пользователя"""
        try:
            # Общее количество достижений
            total_achievements = await self.db.fetchval(
                "SELECT COUNT(*) FROM user_achievements WHERE user_id = $1",
                user_id
            ) or 0
            
            return {
                "total_achievements": total_achievements
            }
            
        except Exception as e:
            logger.error(f"Error getting achievement stats for {user_id}: {e}")
            return {
                "total_achievements": 0
            }
    
    async def get_recent_achievements(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Получить последние достижения пользователя"""
        try:
            result = await self.db.fetch("""
                SELECT ua.achievement_id, ua.earned_at,
                       a.name, a.description, a.icon
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.id
                WHERE ua.user_id = $1
                ORDER BY ua.earned_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Error getting recent achievements for {user_id}: {e}")
            return []
    
    def format_achievement_notification(self, achievement: Dict) -> str:
        """Форматировать уведомление о получении достижения"""
        return f"""🏆 **Новое достижение!**

{achievement['icon']} **{achievement['name']}**
{achievement['description']}"""

    def format_achievement_list(self, achievements: List[Dict], show_earned: bool = True) -> str:
        """Форматировать список достижений"""
        if not achievements:
            return "📭 У вас пока нет достижений"
        
        text = "🏆 **Ваши достижения:**\n\n"
        
        for achievement in achievements:
            status = "✅" if show_earned else "❌"
            
            if show_earned and "earned_at" in achievement:
                earned_date = achievement["earned_at"].strftime("%d.%m.%Y")
                text += f"{status} {achievement['icon']} **{achievement['name']}**\n"
                text += f"   _{achievement['description']}_\n"
                text += f"   📅 Получено: {earned_date}\n\n"
            else:
                text += f"{status} {achievement['icon']} **{achievement['name']}**\n"
                text += f"   _{achievement['description']}_\n\n"
        
        return text
