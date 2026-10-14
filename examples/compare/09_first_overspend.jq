.budget as $budget
| [foreach .expenses[] as $e (0; . + $e)]
| to_entries | map(select(.value > $budget)) | .[0].key
