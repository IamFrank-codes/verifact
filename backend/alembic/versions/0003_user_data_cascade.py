"""Cascade user deletion through owned verification data.

Revision ID: 0003_user_data_cascade
Revises: 0002_email_verification_tokens
"""
from alembic import op

revision = '0003_user_data_cascade'
down_revision = '0002_email_verification_tokens'
branch_labels = None
depends_on = None


def upgrade():
    # Direct user-owned records.
    op.execute("ALTER TABLE public.password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey")
    op.execute("ALTER TABLE public.password_reset_tokens ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE public.verifications DROP CONSTRAINT IF EXISTS verifications_user_id_fkey")
    op.execute("ALTER TABLE public.verifications ADD CONSTRAINT verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE")

    # Verification-owned records, including raw claim/evidence content.
    op.execute("ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_verification_id_fkey")
    op.execute("ALTER TABLE public.claims ADD CONSTRAINT claims_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE public.evidence DROP CONSTRAINT IF EXISTS evidence_claim_id_fkey")
    op.execute("ALTER TABLE public.evidence ADD CONSTRAINT evidence_claim_id_fkey FOREIGN KEY (claim_id) REFERENCES public.claims(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE public.verification_scores DROP CONSTRAINT IF EXISTS verification_scores_verification_id_fkey")
    op.execute("ALTER TABLE public.verification_scores ADD CONSTRAINT verification_scores_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE public.provider_runs DROP CONSTRAINT IF EXISTS provider_runs_verification_id_fkey")
    op.execute("ALTER TABLE public.provider_runs ADD CONSTRAINT provider_runs_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id) ON DELETE CASCADE")

    # This table was added by the app's later Alembic migration, but may not yet
    # exist in every deployment of the separately-managed Supabase schema.
    op.execute("""
        DO $$ BEGIN
            IF to_regclass('public.email_verification_tokens') IS NOT NULL THEN
                ALTER TABLE public.email_verification_tokens DROP CONSTRAINT IF EXISTS email_verification_tokens_user_id_fkey;
                ALTER TABLE public.email_verification_tokens ADD CONSTRAINT email_verification_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)

    # Article text is tied to a verification; remove it only when no other
    # verification still references it. Shared source-catalog rows are retained.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.cleanup_orphaned_verifact_article()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.article_id IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM public.verifications WHERE article_id = OLD.article_id) THEN
                DELETE FROM public.articles WHERE id = OLD.article_id;
            END IF;
            RETURN OLD;
        END;
        $$;
    """)
    op.execute("DROP TRIGGER IF EXISTS cleanup_orphaned_verifact_article_after_verification_delete ON public.verifications")
    op.execute("""
        CREATE TRIGGER cleanup_orphaned_verifact_article_after_verification_delete
        AFTER DELETE ON public.verifications
        FOR EACH ROW EXECUTE FUNCTION public.cleanup_orphaned_verifact_article()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS cleanup_orphaned_verifact_article_after_verification_delete ON public.verifications")
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_orphaned_verifact_article()")
    op.execute("ALTER TABLE public.provider_runs DROP CONSTRAINT IF EXISTS provider_runs_verification_id_fkey")
    op.execute("ALTER TABLE public.provider_runs ADD CONSTRAINT provider_runs_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id)")
    op.execute("ALTER TABLE public.verification_scores DROP CONSTRAINT IF EXISTS verification_scores_verification_id_fkey")
    op.execute("ALTER TABLE public.verification_scores ADD CONSTRAINT verification_scores_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id)")
    op.execute("ALTER TABLE public.evidence DROP CONSTRAINT IF EXISTS evidence_claim_id_fkey")
    op.execute("ALTER TABLE public.evidence ADD CONSTRAINT evidence_claim_id_fkey FOREIGN KEY (claim_id) REFERENCES public.claims(id)")
    op.execute("ALTER TABLE public.claims DROP CONSTRAINT IF EXISTS claims_verification_id_fkey")
    op.execute("ALTER TABLE public.claims ADD CONSTRAINT claims_verification_id_fkey FOREIGN KEY (verification_id) REFERENCES public.verifications(id)")
    op.execute("ALTER TABLE public.verifications DROP CONSTRAINT IF EXISTS verifications_user_id_fkey")
    op.execute("ALTER TABLE public.verifications ADD CONSTRAINT verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)")
    op.execute("ALTER TABLE public.password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey")
    op.execute("ALTER TABLE public.password_reset_tokens ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)")
    op.execute("""
        DO $$ BEGIN
            IF to_regclass('public.email_verification_tokens') IS NOT NULL THEN
                ALTER TABLE public.email_verification_tokens DROP CONSTRAINT IF EXISTS email_verification_tokens_user_id_fkey;
                ALTER TABLE public.email_verification_tokens ADD CONSTRAINT email_verification_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);
            END IF;
        END $$;
    """)
