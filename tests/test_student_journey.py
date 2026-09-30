from scripts.student_journey import run_journey


def test_first_use_correction_undo_search_backup_and_restore(qapp,tmp_path):
    result=run_journey(qapp,tmp_path/'journey')
    assert result['status']=='PASS'
