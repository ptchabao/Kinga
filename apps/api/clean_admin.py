import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import prisma

async def main():
    await prisma.connect()
    
    # 1. Delete user
    user = await prisma.user.find_unique(where={"email": "admin@safiri.ai"})
    if user:
        # Delete UserOrganizationRoles
        await prisma.userorganizationrole.delete_many(where={"userId": user.id})
        # Delete Memberships
        await prisma.membership.delete_many(where={"userId": user.id})
        # Delete user
        await prisma.user.delete(where={"id": user.id})
        print("Deleted user admin@safiri.ai")
        
    # 2. Delete org
    org = await prisma.organization.find_unique(where={"slug": "safiri-ai-hq"})
    if org:
        # Delete roles
        await prisma.role.delete_many(where={"organizationId": org.id})
        # Delete org
        await prisma.organization.delete(where={"id": org.id})
        print("Deleted org safiri-ai-hq")
        
    await prisma.disconnect()

asyncio.run(main())
